# GRP-14
Freesurfer Longitudinal Analysis Pipeline (6.0.1-5)

The current Freesurfer version is based on: freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.1.tar.gz.

## Overview
This gear implements Freesurfer's longitudinal analysis. It reconstructs the surface for each subject individually
and then creates an unbiased template from all time points. Finally, it longitudinally process all timepoints and produces summary statistics. 

IMPORTANT NOTE: By default this Gear DOES NOT save all FreeSurfer outputs, it only retains the summary tables. If you wish to preserve the FreeSurfer outputs you MUST modify the `remove_subjects_dir` configuration option from `True` to `False`. 


## Gear Execution
This gear needs to be run at the [subject level](https://docs.flywheel.io/hc/en-us/articles/360038261213-Run-an-analysis-gear-on-a-subject). By default the pipeline is run on all classified T1 NIfTI files found in all acquisitions for all sessions for the specified subject.

IMPORTANT NOTE: A Freesurfer license file must be supplied. This can be done as an input
file, a configuration option, or as project metadata.  See [this descripiton](https://docs.flywheel.io/hc/en-us/articles/360013235453-How-to-include-a-Freesurfer-license-file-in-order-to-run-the-fMRIPrep-gear-) for more information.

### INPUTS
No gear inputs need are required (see note above regarding FreeSurfer license). The Gear will use a read-only API key at the time of execution to iterate through a given subject's sessions and acquisitions to find all appropriate scans.

### CONFIG
`n_cpus`: [_Optional_] Number of of CPUs/cores to use. Default is all available.

`classification_measurement`: [Optional_] By default the pipeline is run on all classified T1 NIfTI files found in all acquisitions for all sessions for the specified subject. However, you can specify a list containing the specific measurements that a given file must have in order to be included.

`acquisition_regex`: [_Optional_] - By default the gear looks at all acquisitions for candidate input files, however you may specify a regex to only include certain acquisitions across a subject's sessions.

`3T`: [_Optional_] If the T1-weighted scans were acquired on a 3T scanner, set the `3T` 
configuration option.

`remove_subjects_dir`: [_Default=True_] Remove Freesurfer's SUBJECTS_DIR. Do not save and return all of Freesurfer results.  Default is TRUE: remove, don't save.


### OUTPUTS

All outputs are archived (while tables are preserved to the top-level output directory) and may be found in Freesurfer's $SUBJECTS_DIR/:
```
<scrnum>_visit_1
<scrnum>_visit_2
<scrnum>_visit_j
BASE
<scrnum>_visit_1.long.BASE
<scrnum>_visit_2.long.BASE
<scrnum>_visit_j.long.BASE
```

Summary outputs are found in $SUBJECTS_DIR/tables/:
```
<>_aseg_vol.csv
<>_aparc_vol_right.csv
<>_aparc_vol_left.csv
<>_aparc_thick_right.csv
<>_aparc_thick_left.csv
<>_aparc_area_right.csv
<>_aparc_area_left.csv
```

### STATUS
The status of the gear is saved as it is running in the analysis
'info' metadata which can be seen in the "Custom Information" tab
for the analysis on the Flywheel platform.
Example Flywheel SDK python code to list the status is 
provided in
[notebooks/Longitudinal_Status.ipynb](https://github.com/flywheel-apps/GRP-14/blob/dev/notebooks/Longitudinal_Status.ipynb).
