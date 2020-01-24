# GRP-14
Freesurfer Longitudinal Analysis Pipeline (6.0.1-5)

This gear implements Freesurfer's longitudinal analysis. It reconstructs the surface for each subject individually
and then creates an unbiased template from all time points. Finally, it longitudinally process all timepoints and 
produces summary statistics. 

The current Freesurfer version is based on: freesurfer-Linux-centos6_x86_64-stable-pub-v6.0.1.tar.gz.

This gear needs to be run at the subject level.  See [Run an analysis gear on a subject](https://docs.flywheel.io/hc/en-us/articles/360038261213-Run-an-analysis-gear-on-a-subject) for how to do that.  
To be certain that you are running at the subject level when following
those instructions, *be sure* to select (click on) a particular
subject afger pressing the Subject view button.  Then that subject will
be highlighted and instead of the
"Acquisitions" tab next to the Subject view button, you will see the 
"Subject" tab as shown here in the red oval:
![Subject is selected](/images/SubjectSelected.png)
No gear inputs are required.
The longituninal pipeline is run on all T1 NIfTI files found in all 
acquisitions for all sessions for the specified subject.

A Freesurfer license file must be supplied. This can be done as an input
file, a configuration option, or as project metadata.  See [this descripiton](https://docs.flywheel.io/hc/en-us/articles/360013235453-How-to-include-a-Freesurfer-license-file-in-order-to-run-the-fMRIPrep-gear-) for more information.

Output is found in Freesurfer's $SUBJECTS_DIR/:
```
scrnum_visit_1
scrnum_visit_2
scrnum_visit_j
BASE
scrnum_visit_1.long.BASE
scrnum_visit_2.long.BASE
scrnum_visit_j.long.BASE
```

Summary outputs are found in $SUBJECTS_DIR/tables/:
```
ABE4869g_aseg_vol.csv
ABE4869g_aparc_vol_right.csv
ABE4869g_aparc_vol_left.csv
ABE4869g_aparc_thick_right.csv
ABE4869g_aparc_thick_left.csv
ABE4869g_aparc_area_right.csv
ABE4869g_aparc_area_left.csv
```

If the T1-weighted scans were acquired on a 3T scanner, set the "3T" 
configuration option.

The status of the gear is saved as it is running in the analysis
'info' metadata which can be seen in the "Custom Information" tab
for the analysis on the Flywheel platform.
Example Flywheel SDK python code to list the status is 
provided in
[notebooks/Longitudinal_Status.ipynb](https://github.com/flywheel-apps/GRP-14/blob/dev/notebooks/Longitudinal_Status.ipynb).
