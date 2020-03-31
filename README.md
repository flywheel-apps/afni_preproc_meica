# flywheel/me-ica
[Flywheel Gear](https://github.com/flywheel-io/gears/tree/master/spec) to enable the execution of [tedana](https://tedana.readthedocs.io/en/latest/), called through [afni_proc.py](https://afni.nimh.nih.gov/pub/dist/doc/htmldoc/programs/afni_proc.py_sphx.html).

## Introduction
Multi-Echo Independent Components Analysis (ME-ICA) is a method for fMRI analysis and denoising based on the T2* decay of BOLD signals, as measured using multi-echo fMRI. ME-ICA decomposes multi-echo fMRI datasets into independent components (ICs) using FastICA, then categorizes ICs as BOLD or noise using their BOLD and non-BOLD weightings (measured as Kappa and Rho values, respectively). Removing non-BOLD weighted components robustly denoises data for motion, physiology and scanner artifacts, in a simple and physically principled way <sup>[ref](https://github.com/ME-ICA/me-ica/blob/master/README.meica)</sup>. For more information, see:

  > Kundu, P., Inati, S.J., Evans, J.W., Luh, W.M. & Bandettini, P.A. Differentiating BOLD and non-BOLD signals in fMRI time series using multi-echo EPI. NeuroImage (2011).

The tedana package is part of the ME-ICA pipeline, performing TE-dependent analysis of multi-echo functional magnetic resonance imaging (fMRI) data. TE-dependent analysis (tedana) is a Python module for denoising multi-echo functional magnetic resonance imaging (fMRI) data.


tedana originally came about as a part of the [ME-ICA](https://github.com/me-ica/me-ica) pipeline. The ME-ICA pipeline originally performed both pre-processing and TE-dependent analysis of [multi-echo fMRI data](https://tedana.readthedocs.io/en/latest/multi-echo.html); however, tedana now assumes that you’re working with data which has been previously preprocessed.
This gear uses afni_proc to carry out the preprocessing usually required to run tedana.py.

For a summary of multi-echo fMRI, which is the imaging technique tedana builds on, visit Multi-echo fMRI.

For a detailed procedure of how tedana analyzes the data from multi-echo fMRI, visit [Processing pipeline details](https://tedana.readthedocs.io/en/latest/approach.html#).


## Flywheel Usage notes
This Analysis Gear will execute ME-ICA within the Flywheel platform on multi-echo functional data within a given acquisition.

*Please read and understand the following considerations prior to running the Gear on your data.*

### Input
* The user must provide a single input file (DICOM archive containing multi-echo data) from the acquisition on which they wish this Gear to run. The Gear will use that single input file to identify other data within that acquisition to use as input to the algorithm.
* The user may optionally provide an anatomical NIfTI file along with the functional input. This input, if provided, will be used for co-registration.

### Prior to Execution
* **Data within the acquisition must have a Classification set for each file.** The easiest way to do this is to run the `scitran/dicom-mr-classifer` Gear on those data prior to running the DICOM conversion Gear (dcm2niix). The "Classifier" Gear will set the input file's classification, upon which this Gear depends.

* **NIfTI files must be generated for data within the acquisition using the `scitran/dcm2niix` Gear (>=0.6)**. The `dcm2niix` Gear generates file metadata used to set the echo times and (importantly) derive slice timing for each of the given functional inputs. Slice timing information will subsequently be saved out as `slicetimes.txt`.

* **Please make sure that `subject code` and `session label` are set and valid prior to running the Gear.** The `prefix` configuration parameter is parsed from the `subject code` and  `session label` within Flywheel.

### Configuration
* Several configuration parameters can be set at runtime. Please see the `manifest.json` file for the list of parameters and their options.

These configuration options are a subset of the possible config parameters used in afni_proc.py.  Please see their [documentation](https://afni.nimh.nih.gov/pub/dist/doc/program_help/afni_proc.py.html) for more information. 

