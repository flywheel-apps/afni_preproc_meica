#!/usr/bin/env python

import shutil
import logging
import os
import subprocess as sp
from collections import OrderedDict
from pathlib import Path

import htmlark


####################################################################################################
# Constants used in the script, to help decode AFNI's inconsistent key-value scheme.
# Any new settings added to the manigest will also have to be added here. to be added to the call.
# Types:
#   *Path: (could also be a string, I suppose, but this just lets me know it should be a file)
#   *'yn': Lets me know that this is a boolean key, but the key must be followed by a "yes" (or no)
#   *float: Key value is a float
#   *int: Key value is an int
#   *bool: Key is bool.  include the key for true, omit for false.  No value passed with the key.
#   *str: Key value is a string.
#   [...]: Key value is a list of things.  Lets me know to concatenate list values with spaces

supported_afni_opts = OrderedDict()
supported_afni_opts['copy_anat'] = Path
supported_afni_opts['anat_has_skull'] = 'yn'
supported_afni_opts['dsets_me_run'] = [Path]
supported_afni_opts['echo_times'] = [float]
supported_afni_opts['reg_echo'] = str
supported_afni_opts['tcat_remove_first_trs'] = int
supported_afni_opts['cost'] = str
supported_afni_opts['tlrc_base'] = Path
supported_afni_opts['tlrc_NL_warp'] = bool
supported_afni_opts['tlrc_no_ss'] = bool
supported_afni_opts['volreg_align_to'] = str
supported_afni_opts['volreg_align_e2a'] = bool
supported_afni_opts['volreg_tlrc_warp'] = bool
supported_afni_opts['mask_epi_anat'] = 'yn'
supported_afni_opts['combine_method'] = str
supported_afni_opts['combine_opts_tedana'] = float
supported_afni_opts['regress_motion_per_run'] = bool
supported_afni_opts['regress_censor_motion'] = float
supported_afni_opts['regress_censor_outliers'] = float
supported_afni_opts['regress_apply_mot_types'] = str
supported_afni_opts['regress_est_blur_epits'] = bool

# Special lookup dictionary to translate cost function names to AFNI key values.
# There were just too many odd combinations, of things you can do,
# I Could have put more in the manifest, but this is easier.  Feel free to make suggestions.
cost_lookup = {"leastsq": "ls",
               "mutualinfo": 'mi',
               "corratio_mul": "crM",
               "norm_mutualinfo": "nmi",
               "hellinger": "hel",
               "corratio_add": "crA",
               "corratio_uns": "crU",
               "localPcorSigned": "lpc",
               "localPcorAbs": "lpa",
               "localPcor+": "lpc+ZZ",
               "localPcorAbs+": "lpa+ZZ"}
####################################################################################################


log = logging.getLogger(__name__)

def build_afni_proc_call(config):
    
    # Starting command (This version of the gear doesn't change these steps
    command = ['/root/abin/afni_proc.py', '-subj_id', 'data', '-blocks', 'tshift',
               'align', 'tlrc', 'volreg', 'mask', 'combine', 'blur', 'scale', 'regress']

    try:
        for key in supported_afni_opts.keys():
            kind = supported_afni_opts[key]

            if isinstance(kind, list):
                kind = kind[0]

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

                    if isinstance(data, list):
                        data = ' '.join([str(item) for item in data])
                    else:
                        data = '{data}'.format(data=data)

                    append = ['-{}'.format(key)]
                    append.extend('{}'.format(data).split(' '))

                # If the expected type is string
                elif kind == str:
                    data = config[key]

                    if isinstance(data, list):
                        data = ' '.join(data)

                    append = ['-{}'.format(key)]
                    append.extend('{}'.format(data).split(' '))

                # If we need the type to be yn (yes/no), the data coming in is a boolean.
                elif kind == 'yn':
                    data = config[key]
                    if data:
                        data = 'yes'
                    else:
                        data = 'no'

                    append = ['-{}'.format(key)]
                    append.extend('{}'.format(data).split(' '))

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


def run_afni_command(command, output_directory):
    
    # We need to be operating in the output directory.
    os.chdir(output_directory)
    
    # Print the command (also a test of the sp.Popen call)
    echo_command = ['echo']
    echo_command.extend(command)
    sp.Popen(echo_command)

    # Run the main command to build the processing script
    pr = sp.Popen(command, cwd=output_directory)
    pr.wait()
    pr.communicate()
    if pr.returncode != 0:
        log.critical('Error building main processing script')
        return(pr.returncode)
    
    # Run the processing script.
    run_afni = '/usr/bin/tcsh -xef proc.data 2>&1 | tee output.proc.data'
    pr = sp.Popen(run_afni, cwd=output_directory, shell=True)
    pr.wait()
    pr.communicate()
    if pr.returncode != 0:
        log.critical('Error executing main processing script.  See output.proc.data for more info')
        return(pr.returncode)
    
    # If we make it here, pr.returncode is zero, so...
    return(0)
    # I'm going to keep using parenthesis around return statements.  I've been hurt before with 
    # Print statements from python2 -> 3, I'm not making that same mistake twice.


def cleanup_afni_output(output_directory):
    
    data_dir = Path(output_directory,'data.results')
    qc_dir = Path(data_dir, 'QC_data')
    qc_index = Path(qc_dir, 'index.html')
    packed_html = Path(output_directory, 'QC_Snapshot.html')
    
    # First try to copy a standalone html file (with embedded images for viewing in flywheel)
    log.info('Generating standalone QC snapshot')
    try:
        packed = htmlark.convert_page(qc_index)
        
        with open(packed_html, 'w') as packed_html_file:
            packed_html_file.write(packed)
            packed_html_file.close()
    except Exception as e:
        log.warning('Unable to pack standalone QC html report. \
                     Please view the full QC report in the QC zip archive')
        log.exception(e)
    
    # Copy the QC_data directory into a separate file so that it's easy to see and download.
    log.info('Generating separate QC archive')
    try:
        qc_htmlreport_file = Path('/flywheel/v0/output/QC_htmlReport')
        shutil.make_archive(qc_htmlreport_file, 'zip', qc_dir)
    except Exception as e:
        log.warning('Unable to generate QC archive.  Please check the results to ensure \
                    that this directory exists')
        log.exception(e)
    
    # Generate an archive of the entire output
    log.info('Generating archive of entire AFNI output (This may take some time)')
    try:
        afni_output = Path('/flywheel/v0/output/afni_output')
        shutil.make_archive(afni_output, 'zip', data_dir)
        log.info('Removing uncompressed output')
        shutil.rmtree(data_dir)
    except Exception as e:
        log.warning('Unable to generate archive of afni output.')
        log.exception(e)