# GRP-14
Freesurfer Longitudinal Analysis Pipeline

Freesurfer (6.0.1-5) This app implements Freesurfer's longitudinal
analysis. It reconstructs the surface for each subject individually
and then creates a study specific template. The Freesurfer longitudinal
pipeline is used to created subject specific templates. 

The current Freesurfer version is based on: freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.0.tar.gz.

This gear needs to be run at the [subject level](https://docs.flywheel.io/hc/en-us/articles/360038261213-Run-an-analysis-gear-on-a-subject).
No gear inputs need are required.
The longituninal pipeline is run on all T1 NIfTI files found in all 
acquisitions for all sessions for the specified subject.

A Freesurfer license file must be supplied. This can be done as an input
file, a configuration option, or as project metadata.  See [this descripiton](https://docs.flywheel.io/hc/en-us/articles/360013235453-How-to-include-a-Freesurfer-license-file-in-order-to-run-the-fMRIPrep-gear-) for more information.

Output is found in Freesurfer's $SUBJECTS_DIR/:
```
patnum_visit_1
patnum_visit_2
patnum_visit_j
BASE
patnum_visit_1.long.BASE
patnum_visit_2.long.BASE
patnum_visit_j.long.BASE
```

Summary outputs are found in $SUBJECTS_DIR/tables/:
```
freesurfer_aseg_vol.csv
freesurfer_aparc_vol_right.csv
freesurfer_aparc_vol_left.csv
freesurfer_aparc_thick_right.csv
freesurfer_aparc_thick_left.csv
freesurfer_aparc_area_right.csv
freesurfer_aparc_area_left.csv
```

If the T1-weighted scans were acquired on a 3T scanner, set the "3T" 
configuration option.

The status of the gear is saved in "Custom Information" for the analysis
as it is running. Example Flywheel SDK python code to list the status is 
provided in
[notebooks/Longitudinal_Status.ipynb](https://github.com/flywheel-apps/GRP-14/blob/dev/notebooks/Longitudinal_Status.ipynb).

## To Do
This gear has hardcoded values for "study", "scrnum", and "visit"; the
first three columns in the summary output spreadsheets.  These will be
replace by proper values once how to provide them has been decided.

