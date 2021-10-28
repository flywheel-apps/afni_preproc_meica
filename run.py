#!/usr/bin/env python3

import shutil
import logging
import datetime
import os
from pathlib import Path
import psutil
from os import path as op
import json

import flywheel
import afni_utils as af


FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
log = logging.getLogger("meica")
log.setLevel("INFO")


def set_environment(environ_json="/tmp/gear_environ.json"):

    # Let's ensure that we have our environment .json file and load it up
    if op.exists(environ_json):

        # If it exists, read the file in as a python dict with json.load
        with open(environ_json, "r") as f:
            log.info("Loading gear environment")
            environ = json.load(f)

        # Now set the current environment using the keys.  This will automatically be used with any sp.run() calls,
        # without the need to pass in env=...  Passing env= will unset all these variables, so don't use it if you do it
        # this way.
        for key in environ.keys():
            log.debug("{}: {}".format(key, environ[key]))
            os.environ[key] = environ[key]
    else:
        log.warning("No Environment file found!")
    # Pass back the environ dict in case the run.py program has need of it later on.
    return environ


def get_meica_data(context, output_directory="/flywheel/v0/output"):
    """
    For a given input dicom file, grab all of the nifti files from that acquisition.

    Return MEICA data which is a sorted list of file objects.
    """

    # Flywheel Object
    fw = flywheel.Client(context.get_input("api_key")["key"])

    # For this acquisition find each nifti file, download it and note its echo time
    acquisition = fw.get_acquisition(context.get_input("functional")["hierarchy"]["id"])
    nifti_files = [
        x
        for x in acquisition.files
        if x.type == "nifti" and "Functional" in x.classification["Intent"]
    ]
    log.info(
        "Found %d Functional NIfTI files in %s" % (len(nifti_files), acquisition.label)
    )

    # Compile meica_data structure
    meica_data = []
    repetition_time = ""
    for n in nifti_files:
        file_path = os.path.join(output_directory, n.name)
        log.info("Downloading %s" % (n.name))
        fw.download_file_from_acquisition(acquisition.id, n.name, file_path)
        echo_time = n.info.get("EchoTime")

        # TODO: Handle case where EchoTime is not here
        # or classification is not correct
        # Or not multi echo data
        # Or if coronavirus attacks

        meica_data.append({"path": n.name, "te": echo_time * 1000})  # Convert to ms

    # Generate prefix
    sub_code = (
        fw.get_session(acquisition.parents.session)
        .subject.code.strip()
        .replace(" ", "")
    )
    label = acquisition.label.strip().replace(" ", "")
    prefix = "%s_%s" % (sub_code, label)

    meica_data = sorted(meica_data, key=lambda k: k["te"])
    datasets = [Path(meica["path"]) for meica in meica_data]
    tes = [meica["te"] for meica in meica_data]

    return (datasets, tes)


def log_system_resources():
    log.info(
        "Logging System Resources\n\n==============================================================================\n"
    )
    try:
        log.info("CPU Count: \t %s", psutil.cpu_count())
        log.info("CPU Speed: \t %s", psutil.cpu_freq())
        log.info("Virtual Memory: \t %s", psutil.virtual_memory())
        log.info("Swap Memory: \t %s", psutil.swap_memory())
        log.info("Disk Usage: \t %s", psutil.disk_usage("/"))
    except Exception as e:
        log.warning("Error Logging system info.  Attempted to retrieve the following:")
        log.info("CPU Count")
        log.info("CPU Speed")
        log.info("Virtual Memory")
        log.info("Swap Memory")
        log.info("Disk Usage")

    log.info(
        "\n\n==============================================================================\n"
    )


def main(context):

    environ = set_environment()

    log.info("  start: %s" % datetime.datetime.utcnow())
    return_code = 0

    ############################################################################
    # READ CONFIG
    config = context.config

    ############################################################################
    # FIND AND DOWNLOAD DATA
    output_directory = "/flywheel/v0/output"
    datasets, tes = get_meica_data(context, output_directory)

    ############################################################################
    # INPUTS
    anatomical_input = context.get_input_path("anatomical")

    # Anatomical nifti must be in the output directory when running meica
    anatomical_nifti = os.path.join(
        output_directory, os.path.basename(anatomical_input)
    )

    # If a file with the same name as the anatomical exists already, we must rename it so afni can run correctly.
    if os.path.exists(anatomical_nifti):
        # Strip down to the first extension dot
        basename = os.path.basename(anatomical_input)
        first_dot = basename.find('.')
        # and add "_T1" to the name, reappending the extension
        basename = basename[:first_dot] + "_T1" + basename[first_dot:]
        anatomical_nifti = os.path.join(output_directory, basename)

    shutil.copyfile(anatomical_input, anatomical_nifti)
    # anatomical_nifti = context.get_input_path('anatomical')

    shutil.copyfile(anatomical_input, anatomical_nifti)

    # Set up some keys in config that will be used to build the AFNI call.
    config["copy_anat"] = Path(anatomical_nifti)
    config["dsets_me_run"] = datasets
    config["echo_times"] = tes
    config["tlrc_base"] = Path("/root/abin/{}".format(config["tlrc_base"]))
    config[
        "combine_opts_tedana"
    ] = "DUMMY"  # This just needs to be here because of the wonky
    # Way I build the NIFTI argument.  Nicolas, before you say it, yes, I'm sure NiPype would help.

    # Build the AFNI command
    log.info("Building AFNI command")
    try:
        command = af.build_afni_proc_call(config)
    except Exception as e:
        log.error("Error generating the AFNI command")
        log.exception(e)
        # If we can't build the call, we can't run it.  Return a nonzero exit code
        return 1

    # Run the AFNI command
    log.info("Running AFNI command")
    try:
        return_code = af.run_afni_command(command, output_directory)
    except Exception as e:
        log.error("Error running the AFNI command")
        log.exception(e)
        # It's possible there are files to clean up.  so continue running, but if this part crashed,
        # We consider the gear failed
        return_code = 1

    # Cleanup the AFNI output/make nice for flywheel output containers:
    log.info("Cleaning up AFNI output")
    try:
        # If it's not successful and the user did not ask to save output on error:
        if return_code != 0 and not config["save-output-on-error"]:
            # Remove the directory
            os.rmdir(output_directory)
            # And remake it in case that messes things up with flywheel later idk
            os.mkdir(output_directory)

        af.cleanup_afni_output(output_directory)
    except Exception as e:
        log.error("Error cleaning up AFNI output directory")
        log.exception(e)
        return_code = 1

    return return_code


if __name__ == "__main__":
    log_system_resources()

    with flywheel.gear_context.GearContext() as gear_context:
        # gear_context.init_logging()
        # Error here when running from command line (even with manifest)
        # gear_context.log_config()
        exit_status = main(gear_context)

    log.info("exit_status is %s", exit_status)
    os.sys.exit(exit_status)
