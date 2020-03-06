#!/usr/bin/env python

import json
import shutil
import zipfile
import logging
import datetime
import os
import subprocess as sp
from collections import OrderedDict
from pathlib import Path

import flywheel


#### Setup logging as per SSE best practices (Thanks Andy!)
fmt = '%(asctime)s %(levelname)8s %(name)-8s - %(message)s'
logging.basicConfig(format=fmt)
log = logging.getLogger('[flywheel/MSOT-mouse-recon]')

supported_afni_opts = OrderedDict()
supported_afni_opts['copy_anat']=Path
supported_afni_opts['anat_has_skull']='yn'
supported_afni_opts['dsets_me_run']=[Path]
supported_afni_opts['echo_times']=[float]
supported_afni_opts['reg_echo']=str
supported_afni_opts['tcat_remove_first_trs']=int
supported_afni_opts['cost']=str
supported_afni_opts['tlrc_base']=Path
supported_afni_opts['tlrc_NL_warp']=bool
supported_afni_opts['tlrc_no_ss']=bool
supported_afni_opts['volreg_align_to']=str
supported_afni_opts['volreg_align_e2a']=bool
supported_afni_opts['volreg_tlrc_warp']=bool
supported_afni_opts['mask_epi_anat']='yn'
supported_afni_opts['combine_method']=str
supported_afni_opts['combine_opts_tedana']=float
supported_afni_opts['regress_motion_per_run']=bool
supported_afni_opts['regress_censor_motion']=float
supported_afni_opts['regress_censor_outliers']=float
supported_afni_opts['regress_apply_mot_types']=str
supported_afni_opts['regress_est_blur_epits']=bool

cost_lookup = {"leastsq":"ls",
        "mutualinfo":'mi',
        "corratio_mul":"crM",
        "norm_mutualinfo":"nmi",
        "hellinger":"hel",
        "corratio_add":"crA",
        "corratio_uns":"crU",
        "localPcorSigned":"lpc",
        "localPcorAbs":"lpa",
        "localPcor+":"lpc+ZZ",
        "localPcorAbs+":"lpa+ZZ"}




def zipdir(dirPath=None, zipFilePath=None, includeDirInZip=True, deflate=True):
    """Create a zip archive from a directory.

    Note that this function is designed to put files in the zip archive with
    either no parent directory or just one parent directory, so it will trim any
    leading directories in the filesystem paths and not include them inside the
    zip archive paths. This is generally the case when you want to just take a
    directory and make it into a zip file that can be extracted in different
    locations.

    Keyword arguments:

    dirPath -- string path to the directory to archive. This is the only
    required argument. It can be absolute or relative, but only one or zero
    leading directories will be included in the zip archive.

    zipFilePath -- string path to the output zip file. This can be an absolute
    or relative path. If the zip file already exists, it will be updated. If
    not, it will be created. If you want to replace it from scratch, delete it
    prior to calling this function. (default is computed as dirPath + ".zip")

    includeDirInZip -- boolean indicating whether the top level directory should
    be included in the archive or omitted. (default True)

"""
    if deflate:
        mode = zipfile.ZIP_DEFLATED
    else:
        mode = zipfile.ZIP_STORED
    if not zipFilePath:
        zipFilePath = dirPath + ".zip"
    if not os.path.isdir(dirPath):
        raise OSError("dirPath argument must point to a directory. "
            "'%s' does not." % dirPath)
    parentDir, dirToZip = os.path.split(dirPath)
    #Little nested function to prepare the proper archive path
    def trimPath(path):
        archivePath = path.replace(parentDir, "", 1)
        if parentDir:
            archivePath = archivePath.replace(os.path.sep, "", 1)
        if not includeDirInZip:
            archivePath = archivePath.replace(dirToZip + os.path.sep, "", 1)
        return os.path.normcase(archivePath)

    outFile = zipfile.ZipFile(zipFilePath, "w", mode, allowZip64=True)
    for (archiveDirPath, dirNames, fileNames) in os.walk(dirPath):
        for fileName in fileNames:
            filePath = os.path.join(archiveDirPath, fileName)
            outFile.write(filePath, trimPath(filePath))
        # Make sure we get empty directories as well
        if not fileNames and not dirNames:
            zipInfo = zipfile.ZipInfo(trimPath(archiveDirPath) + "/")
            outFile.writestr(zipInfo, "")
    outFile.close()

def debug_get_meica_data(config, output_directory='/flywheel/v0/output'):
    """
    For a given input dicom file, grab all of the nifti files from that acquisition.

    Return MEICA data which is a sorted list of file objects.
    """

    # Flywheel Object
    fw = flywheel.Client(config['inputs']['api_key']['key'])

    # For this acquisition find each nifti file, download it and note its echo time
    acquisition = fw.get_acquisition(config['inputs'].get('functional').get('hierarchy').get('id'))
    nifti_files = [ x for x in acquisition.files
                        if x.type == 'nifti'
                        and "Functional" in x.classification['Intent']
                  ]
    log.info('Found %d Functional NIfTI files in %s' % (len(nifti_files), acquisition.label))

    # Compile meica_data structure
    meica_data = []
    repetition_time = ''
    for n in nifti_files:
        file_path = os.path.join(output_directory, n.name)
        log.info('Downloading %s' % (n.name))
        fw.download_file_from_acquisition(acquisition.id, n.name, file_path)
        echo_time = n.info.get('EchoTime')
 
        # TODO: Handle case where EchoTime is not here
        # or classification is not correct
        # Or not multi echo data
        # Or if coronavirus attacks 

        meica_data.append({
                "path": n.name,
                "te": echo_time*1000 # Convert to ms
            })

    # Generate prefix
    sub_code = fw.get_session(acquisition.parents.session).subject.code.strip().replace(' ','')
    label = acquisition.label.strip().replace(' ','')
    prefix = '%s_%s' % (sub_code, label)
    
    meica_data = sorted(meica_data, key=lambda k: k['te'])
    datasets = [Path(meica['path']) for meica in meica_data]
    tes = [meica['te'] for meica in meica_data]
    


    return(datasets,tes)

def get_meica_data(context, output_directory='/flywheel/v0/output'):
    """
    For a given input dicom file, grab all of the nifti files from that acquisition.

    Return MEICA data which is a sorted list of file objects.
    """

    # Flywheel Object
    fw = flywheel.Client(context.get_input('api_key')['key'])

    # For this acquisition find each nifti file, download it and note its echo time
    acquisition = fw.get_acquisition(context.get_input('functional')['hierarchy']['id'])
    nifti_files = [ x for x in acquisition.files
                        if x.type == 'nifti'
                        and "Functional" in x.classification['Intent']
                  ]
    log.info('Found %d Functional NIfTI files in %s' % (len(nifti_files), acquisition.label))

    # Compile meica_data structure
    meica_data = []
    repetition_time = ''
    for n in nifti_files:
        file_path = os.path.join(output_directory, n.name)
        log.info('Downloading %s' % (n.name))
        #fw.download_file_from_acquisition(acquisition.id, n.name, file_path)
        echo_time = n.info.get('EchoTime')
 
        # TODO: Handle case where EchoTime is not here
        # or classification is not correct
        # Or not multi echo data
        # Or if coronavirus attacks 

        meica_data.append({
                "path": n.name,
                "te": echo_time*1000 # Convert to ms
            })

    # Generate prefix
    sub_code = fw.get_session(acquisition.parents.session).subject.code.strip().replace(' ','')
    label = acquisition.label.strip().replace(' ','')
    prefix = '%s_%s' % (sub_code, label)
    
    meica_data = sorted(meica_data, key=lambda k: k['te'])
    datasets = [Path(meica['path']) for meica in meica_data]
    tes = [meica['te'] for meica in meica_data]
    


    return(datasets,tes)



def log_system_resources():
    log.info('Logging System Resources\n\n==============================================================================\n')
    try:
        log.info('CPU Count: \t %s', psutil.cpu_count())
        log.info('CPU Speed: \t %s', psutil.cpu_freq())
        log.info('Virtual Memory: \t %s', psutil.virtual_memory())
        log.info('Swap Memory: \t %s', psutil.swap_memory())
        log.info('Disk Usage: \t %s', psutil.disk_usage('/'))
    except Exception as e:
        log.warning('Error Logging system info.  Attempted to retrieve the following:')
        log.info('CPU Count')
        log.info('CPU Speed')
        log.info('Virtual Memory')
        log.info('Swap Memory')
        log.info('Disk Usage')
        
    log.info('\n\n==============================================================================\n')
    
    
def build_afni_proc_call(config):
    
    # Starting command (This version of the gear doesn't change these steps
    command = ['/root/abin/afni_proc.py', '-subj_id', 'data', '-blocks', 'tshift',
               'align', 'tlrc', 'volreg', 'mask', 'combine', 'blur', 'scale', 'regress']
    
    try:
        for key in supported_afni_opts.keys():
            kind = supported_afni_opts[key]
            
            if isinstance(kind,list):
                kind=kind[0]
                
            if key in config:
                
                # a couple odd cases to address
                if key == 'cost':
                    data = cost_lookup[config[key]]
                    append = ['-align_opts_aea', '-{}'.format(key), '{}'.format(data)]
                    
                elif key == 'combine_opts_tedana':
                    data = config['kdaw']
                    append = ['-{}'.format(key), '--kdaw={}'.format(data)]
                    
                # If the expected type is Path
                elif kind == Path or kind == int or kind == float:
                    data = config[key]
                    
                    if isinstance(data,list):
                        data = ' '.join([str(item) for item in data])
                    else:
                        data = '{data}'.format(data=data)
                    
                    append = ['-{}'.format(key), '{}'.format(data)]
                    
                # If the expected type is string
                elif kind == str:
                    data = config[key]
                    
                    if isinstance(data,list):
                        data = ' '.join(data)

                    append = ['-{}'.format(key), '{}'.format(data)]
                    
                # If we need the type to be yn (yes/no), the data coming in is a boolean.
                elif kind == 'yn':
                    data = config[key]
                    if data:
                        data = 'yes'
                    else:
                        data = 'no'

                    append = ['-{}'.format(key), '{}'.format(data)]
                    
                elif kind == bool:
                    data = config[key]
                    append = ''
                    if data:
                        append = ['-{}'.format(key)]
                    
                command.extend(append)
                
    except Exception as e:
        log.exception(e)
        raise e
    
    log.info(command)
    
    return(command)
                
                






def main(context):
    """
    Run meica on a given dataset.
    """

    # logging.basicConfig(level=gear_context.config['gear-log-level'], format=fmt)
    log.setLevel(context.config['gear-log-level'])
    log.info('log level is ' + context.config['gear-log-level'])
    context.log_config()  # not configuring the log but logging the config
    config = context.config

    log.setLevel(getattr(logging, 'DEBUG'))
    logging.getLogger('MEICA').setLevel(logging.INFO)
    log.info('  start: %s' % datetime.datetime.utcnow())
    
    log_system_resources()

    ############################################################################
    # READ CONFIG

    CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    with open(CONFIG_FILE_PATH, 'r') as config_file:
        config = json.load(config_file)


    ############################################################################
    # FIND AND DOWNLOAD DATA

    output_directory = '/flywheel/v0/output'
    meica_data, prefix, tpattern_file, repetition_time = get_meica_data(config, output_directory)


    ############################################################################
    # INPUTS

    if config['inputs'].get('anatomical'): # Optional
        anatomical_input = config['inputs'].get('anatomical').get('location').get('path')

        # Anatomical nifti must be in the output directory when running meica
        anatomical_nifti = os.path.join(output_directory, os.path.basename(anatomical_input))
        shutil.copyfile(anatomical_input, anatomical_nifti)
    else:
        anatomical_nifti = ''

    if config['inputs'].get('slice_timing'): # Optional
        slice_timing_input = config['inputs'].get('slice_timing').get('location').get('path')

        # File must be in the output directory when running meica
        slice_timing_file = os.path.join(output_directory, os.path.basename(slice_timing_input))
        shutil.copyfile(slice_timing_input, slice_timing_file)
    else:
        slice_timing_input = ''


    ############################################################################
    # CONFIG OPTIONS

    basetime = config.get('config').get('basetime') # Default = "0"
    mni = config.get('config').get('mni') # Default = False
    tr = config.get('config').get('tr', '') # No default
    if not tr and repetition_time:
        tr = repetition_time
    cpus = config.get('config').get('cpus')
    no_axialize = config.get('config').get('no_axialize')
    native = config.get('config').get('native')
    keep_int = config.get('config').get('keep_int')
    tpattern_gen = config.get('config').get('tpattern_gen')
    daw = config.get('config').get('daw')

    ############################################################################
    # RUN MEICA

    dataset_cmd = '-d %s' % (','.join([ x['path'] for x in meica_data ]))
    echo_cmd = '-e %s' % (','.join([ str(x['te']) for x in meica_data ]))
    anatomical_cmd = '-a %s' % (os.path.basename(anatomical_nifti)) if anatomical_nifti else ''
    mni_cmd = '--MNI' if mni else ''
    tr_cmd = '--TR %s' % (str(tr)) if tr else ''
    cpus_cmd = '--cpus %s' % (str(cpus)) if cpus else ''
    no_axialize_cmd = '--no_axialize' if no_axialize else ''
    native_cmd = '--native' if native else ''
    keep_int_cmd = '--keep_int' if keep_int else ''
    if slice_timing_input:
        tpattern_cmd = '--tpattern=@%s' % (os.path.basename(slice_timing_input))
        log.info('Using user-provided slice-timing file...')
    else:
        tpattern_cmd = '--tpattern=@%s' % (tpattern_file) if tpattern_file and tpattern_gen else ''

    # Run the command
    command = 'cd %s && /flywheel/v0/me-ica/meica.py %s %s -b %s %s %s %s %s %s %s %s %s --prefix %s --daw %s' % ( output_directory,
            dataset_cmd,
            echo_cmd,
            basetime,
            anatomical_cmd,
            mni_cmd,
            tr_cmd,
            cpus_cmd,
            no_axialize_cmd,
            native_cmd,
            keep_int_cmd,
            tpattern_cmd,
            prefix,
            daw )

    log.info(command)
    status = os.system(command)

    if status == 0:
        log.info('Command exited with 0 status. Compressing outputs...')
        dirs = [ os.path.join(output_directory, x)
                        for x in os.listdir(output_directory)
                        if os.path.isdir(os.path.join(output_directory, x))
                ]
        for d in dirs:
            out_zip = os.path.join(output_directory, os.path.basename(d) + '.zip')
            log.info('Generating %s... ' % (out_zip))
            zipdir(d, out_zip, os.path.basename(d))
            shutil.rmtree(d)

    log.info('Done: %s' % datetime.datetime.utcnow())

    os.sys.exit(status)

def debug_config():
    config={"gear-log-level": "DEBUG", 
            "reg_echo": 2,
            "type": "integer",
            "tcat_remove_first_trs": 0,
            "cost":"localPcor+",
            "cpus": 2,
            "tlrc_base": "MNI152_T1_2009c+tlrc",
            "nonlinear_warp": True,
            "daw": 10,
            "volreg_align_e2a": True,
            "volreg_tlrc_warp":True,
            "volreg_align_to":"MIN_OUTLIER",
            "anat_has_skull": False,
            "tlrc_no_ss": True,
            "regress_motion_per_run":True,
            "regress_censor_motion": 0.2,
            "mask_epi_anat": True,
            "smoothing": 4,
            "regress_censor_outliers":0.05,
            "regress_apply_mot_types":"demean deriv",
            "regress_est_blur_epits":True,
            "combine_method": "tedana_OC",
            "dsets_me_run": [Path('/home/data1/'),Path('/home/data2'),Path('/home/data3')],
            'echo_times': [1.0,2.0,3.0],
            "copy_anat": '/home/test/anatomical',
            'tlrc_base' : Path('/root/abin/MNI152_2009c+tlrc'),
            'combine_opts_tedana':'Dummy.  Points to kdaw'}
    return(config)

def debug_main(context):
    
    # logging.basicConfig(level=gear_context.config['gear-log-level'], format=fmt)


    log.setLevel(getattr(logging, 'DEBUG'))
    logging.getLogger('MEICA').setLevel(logging.INFO)
    log.info('  start: %s' % datetime.datetime.utcnow())

    log_system_resources()

    ############################################################################
    # READ CONFIG

    ############################################################################
    # READ CONFIG

    # CONFIG_FILE_PATH = '/flywheel/v0/config.json'
    # with open(CONFIG_FILE_PATH, 'r') as config_file:
    #     context = json.load(config_file)
    config=context.config
    #config = debug_config()
    ############################################################################
    # FIND AND DOWNLOAD DATA

    output_directory = '/flywheel/v0/output'
    datasets, tes = get_meica_data(context, output_directory)
    ############################################################################
    # INPUTS

    anatomical_input = context.get_input_path('anatomical')

    # Anatomical nifti must be in the output directory when running meica
    anatomical_nifti = os.path.join(output_directory, os.path.basename(anatomical_input))
    shutil.copyfile(anatomical_input, anatomical_nifti)

    config['copy_anat'] = Path(anatomical_nifti)
    config['dsets_me_run'] = datasets
    config['echo_times'] = tes
    config['tlrc_base'] = Path('/root/abin/{}'.format(config['tlrc_base']))
    config['combine_opts_tedana'] = 'DUMMY'
    
    command = build_afni_proc_call(config)
    print(command)
    
    os.chdir(output_directory)
    pr = sp.Popen(command)
    pr.wait()
    
    run_afni = ['tcsh', '-xef', 'proc.data', '2>&1', '|', 'tee output.proc.data']
    
    pr = sp.Popen(run_afni)
    pr.wait()
    
    
    return 0

if __name__ == '__main__':
    log_system_resources()
    
    with flywheel.gear_context.GearContext() as gear_context:
        #gear_context.init_logging()
        # Error here when running from command line (even with manifest)
        # gear_context.log_config()
        exit_status = debug_main(gear_context)

    log.info('exit_status is %s', exit_status)
    os.sys.exit(exit_status)