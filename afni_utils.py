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
import psutil
import flywheel








####################################################################################################
# Constants used in the script
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
####################################################################################################


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

    return (command)




