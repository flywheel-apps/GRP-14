# GRP-14
Freesurfer Longitudinal Analysis Pipeline (6.0.1-5)

## Overview
This gear implements [Freesurfer's longitudinal analysis](https://surfer.nmr.mgh.harvard.edu/fswiki/LongitudinalProcessing).
It reconstructs the surface for each subject individually
and then creates an unbiased template from all time points. Finally, it longitudinally process all timepoints and 
produces summary statistics. 

The current Freesurfer version is based on: freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.1.tar.gz.

IMPORTANT NOTE: By default this Gear DOES NOT save all FreeSurfer outputs, it only retains the summary tables. If you wish to preserve the FreeSurfer outputs you MUST modify the `remove_subjects_dir` configuration option from `True` (checked) to `False` (un-checked).

## Gear Execution
This gear needs to be run at the subject level.  See [Run an analysis gear on a subject](https://docs.flywheel.io/hc/en-us/articles/360038261213-Run-an-analysis-gear-on-a-subject) for how to do that.  

To be certain that you are running at the subject level when following
those instructions, the *most important step* is to select (click on) a 
particular subject after pressing the Subject view button.  Then that subject 
will be highlighted and next to the Subject view button, instead of the
"Acquisitions" tab as shown here in the red oval:
![Acquisitions is selected](/images/AcquisitionsSelected.png)

You will see the "Subject" tab next to the Subject view button like this:
![Subject is selected](/images/SubjectSelected.png)
Above, the subject "126_S_1221" was selected and is highlighted in light blue.

Then click on the "Analyses" tab to find the "Run Analysis Gear" button that
will launch the gear.
![Analyses is selected](/images/AnalysesSelected.png)
Note that the "Subject" tab is still next to the Subject view button instead of
the "Acquisitions" tab, which is now missing.

### INPUTS
No scan inputs are required for this gear.  The longitudinal pipeline
will be run on all T1 NIfTI files found in all acquisitions for all
sessions for the specified subject. That is, the Gear will use a
read-only API key at the time of execution to iterate through a
given subject's sessions and acquisitions to find all appropriate
scans.

IMPORTANT NOTE: A Freesurfer license file must be supplied. This can be done as an input
file, a configuration option, or as project metadata.  See [this description](https://docs.flywheel.io/hc/en-us/articles/360013235453-How-to-include-a-Freesurfer-license-file-in-order-to-run-the-fMRIPrep-gear-) for more information.


### CONFIG
`n_cpus`: [_Optional_] Number of of CPUs/cores to use. Default is all available.

`classification_measurement`: [_Optional_] By default the pipeline is run on all classified T1 NIfTI files found in all acquisitions for all sessions for the specified subject. However, you can specify a list containing the specific measurements that a given file must have in order to be included.

`acquisition_regex`: [_Optional_] - By default the gear looks at all acquisitions for candidate input files, however you may specify a regex to only include certain acquisitions across a subject's sessions.

`3T`: [_Optional_] If the T1-weighted scans were acquired on a 3T scanner, set the `3T` 
configuration option.

`remove_subjects_dir`: [_Default=True_] Remove Freesurfer's SUBJECTS_DIR. Do not save and return all of Freesurfer results.  Default is TRUE: remove, don't save.  That is, this gear does *not* save the full Freesurfer output by default.  If you *do* want to save all of the Freesurfer output, un-check this option.

### OUTPUTS
The results of this gear are .csv files that can be viewed individually on the 
platform.  They can also be viewed locally by downloading the .zip archive that
contains all of the .csv files.

These .csv files are named using the name of the project and the measurement.  Inside each .csv file, the first three columns are the project name, the subject
name, and the session label.  The subject name and session label here may be
different from what you see on the Flywheel platform because they are are 
stripped of any characters that are not numbers, digits, or an underscore.

If the full Freesurfer output is not removed, the .zip archive will
contain individual time points in Freesurfer's $SUBJECTS_DIR/, which
is set to the Flywheel project name.  There will also be a directory
called "BASE" and additional directories, one for each time point with
".long.BASE" appended.  These contain the results from the [3 longitudinal
pipeline steps](https://surfer.nmr.mgh.harvard.edu/fswiki/LongitudinalProcessing#WorkflowSummary), "cross-sectional", "template", and "longitudinal".


```
ProjectName/
    SubjectCode-SessionLabel/
    SubjectCode-SessionLabel/
    SubjectCode-SessionLabel/
    BASE/
    SubjectCode-SessionLabel.long.BASE/
    SubjectCode-SessionLabel.long.BASE/
    SubjectCode-SessionLabel.long.BASE/
```

Summary outputs are found in $SUBJECTS_DIR/tables/:
```
ProjectName/
    tables/
        ProjectName_aseg_vol.csv
        ProjectName_aparc_vol_right.csv
        ProjectName_aparc_vol_left.csv
        ProjectName_aparc_thick_right.csv
        ProjectName_aparc_thick_left.csv
        ProjectName_aparc_area_right.csv
        ProjectName_aparc_area_left.csv
```

The .zip archive is created if the `gear-zip-output` configuration option
is true (checked).  This is the default.  If you un-check this option, the
individual files will be available to view/download on the platform
individually.  If you uncheck this option and also uncheck 
`remove_subjects_dir` so that Freesurfer's full output is not removed, 
there will be *very* many files in the output, which is probably not 
what you want.

### STATUS
The status of the gear is saved as it is running in the analysis
'info' metadata which can be seen in the "Custom Information" tab
for the analysis on the Flywheel platform.
Example Flywheel SDK python code to list the status is 
provided in
[notebooks/Longitudinal_Status.ipynb](https://github.com/flywheel-apps/GRP-14/blob/dev/notebooks/Longitudinal_Status.ipynb).
