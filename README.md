# GRP-14
Freesurfer Longitudinal Analysis Pipeline (6.0.1-5)

This gear implements [Freesurfer's longitudinal analysis](https://surfer.nmr.mgh.harvard.edu/fswiki/LongitudinalProcessing#WorkflowSummary).
It reconstructs the surface for each subject individually
and then creates an unbiased template from all time points. Finally, it longitudinally process all timepoints and 
produces summary statistics. 

The current Freesurfer version is based on: freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.1.tar.gz.

No gear inputs are required.
This gear needs to be run at the subject level.  See [Run an analysis gear on a subject](https://docs.flywheel.io/hc/en-us/articles/360038261213-Run-an-analysis-gear-on-a-subject) for how to do that.  

To be certain that you are running at the subject level when following
those instructions, the *most important step* is to select (click on) a 
particular subject after pressing the Subject view button.  Then that subject 
will be highlighted and next to the Subject view button, instead of the
"Acquisitions" tab as shown here in the red oval:
![Acquisitiions is selected](/images/AcquisitionsSelected.png)

You will see the "Subject" tab next to the Subject view button like this:
![Subject is selected](/images/SubjectSelected.png)
Above, the subject "126_S_1221" was selected and is highlighted in light blue.

Then click on the "Analyses" tab to find the "Run Analysis Gear" button that
will launch the gear.
![Analyses is selected](/images/AnalysesSelected.png)
Note that the "Subject" tab is still next to the Subjet view button instead of
the "Acqusitions" tab, which is now missing.

The longituninal pipeline is run on all T1 NIfTI files found in all 
acquisitions for all sessions for the specified subject.

A Freesurfer license file must be supplied. This can be done as an input
file, a configuration option, or as project metadata.  See [this descripiton](https://docs.flywheel.io/hc/en-us/articles/360013235453-How-to-include-a-Freesurfer-license-file-in-order-to-run-the-fMRIPrep-gear-) for more information.

The results of this gear are .csv files that can be viewed individually on the 
platform.  They can also be viewed locally by downloading the .zip archive that
contains all of the .csv files.

These .csv files are named using the name of the project and the measurement.  
Inside each .csv file, the first three columns are the project name, the subject
name, and the session label.  The subject name and session label here may be
different from what you see on the Flywheel platform because they are are 
stripped of any characters that are not numbers, digits, or an underscore.

This gear does *not* save the full Freesurfer output by default.  Note that 
there is a configuration option called "remove_subjects_dir".  If you *do* want 
to save all of the Freesurfer output, un-check it.  This will set it to false
so that all of the Freesurfer subject directories will not be removed.
Instead, they will end up in the .zip archive along with the .csv files.

If the full Freesurfer output is not removed, the .zip archive will
contain individual time points in Freesurfer's $SUBJECTS_DIR/, which
is set to the Flywheel project name.  There will also be a directory
called "BASE" and additional directories, one for each time point with
".long.BASE" appended.  These contain the results from the 3 longitudinal
pipeline steps.


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

The .zip archive is created if the "gear-zip-output" configuration option
is true (checked).  This is the default.  If you un-check this option, the
individual files will be available to view/download on the platform
individually.  If you uncheck this option and also uncheck 
"remove_subjects_dir" so that Freesurfer's full output is not removed, 
there will be *very* many files in the output, which is probably not 
what you want.

If the T1-weighted scans were acquired on a 3T scanner, set the "3T" 
configuration option.

The status of the gear is saved as it is running in the analysis
'info' metadata which can be seen in the "Custom Information" tab
for the analysis on the Flywheel platform.
Example Flywheel SDK python code to list the status is 
provided in
[notebooks/Longitudinal_Status.ipynb](https://github.com/flywheel-apps/GRP-14/blob/dev/notebooks/Longitudinal_Status.ipynb).
