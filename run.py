#!/usr/bin/env python3
"""Run the gear: set up for and call Freesurfer Longitudinal Processing.

Description
  - Cross-sectional and longitudinal FreeSurfer proessing for a
    single patient with multiple scans
  - Collect all longitudinal FreeSurfer results into summary tables

Process
  - Execute cross-sectional processing for each Nifti nii_j with
    coresponding scan (visit) ID visit_j
      % recon-all -s visit_j -i nii_j -all -qcache [-3T]
  - Create the unbiased template
      % recon-all -base BASE -tp visit_1 -tp visit_2 ... -tp visit_N \
         -all -qcache [-3T]
  - Execute longitudinal processing for each scan (visit)
      % recon-all -long visit_j BASE -all -qcache [-3T]
  - The -3T option is included if B0=3.0 is in the Nifti "descrip"

Freesurfer Output Structure
       <destdir>/<patnum>/visit_j
       <destdir>/<patnum>/BASE
       <destdir>/<patnum>/visit_j.long.BASE

Summary Outputs (produced by abe_freesurfer_tables.py)
  freesurfer_aseg_vol.csv
  freesurfer_aparc_vol_right.csv
  freesurfer_aparc_vol_left.csv
  freesurfer_aparc_thick_right.csv
  freesurfer_aparc_thick_left.csv
  freesurfer_aparc_area_right.csv
  freesurfer_aparc_area_left.csv

Original perl coding by: DB Clayton - 2019/09/17

"""

import os
import sys
import logging
import shutil
import json

import flywheel

from utils.license.freesurfer import find_freesurfer_license

from utils.fly.custom_log import custom_log 
from utils.fly.load_manifest_json import load_manifest_json 
from utils.fly.make_file_name_safe import make_file_name_safe

from utils.results.set_zip_name import set_zip_head
from utils.results.zip_output import zip_output

import utils.dry_run

import utils.system


def download_files(context):
    """Download apropriate files for the subject

    Search through all files for all acquisitions for all sessions for this
    subject and download only the T1 nifti files.  If file names are repeated
    a number is prepended. Troublesome characters in the file name are replaced
    with "_".  The file's original name, full path, and creation date are 
    logged.
    
    Args:
        context (dict): the gear context 
        See https://flywheel-io.github.io/core/branches/master/python/sdk_gears.html

    Returns:
        Sets context.gear_dict['niftis'] to a list of the local paths to each
        file.
    """

    niftis = []
    rpt = 1
    fw = context.client

    # go through all sessions, acquisitions to find files
    sessions = context.gear_dict['subject'].sessions()

    for session in sessions:

        acquisitions = fw.get_session_acquisitions(session.id)

        for acquisition in acquisitions:

            for afile in acquisition.files:

                # Run on ALL T1 nifti files TODO limit this
                if afile.type == 'nifti' and \
                   'T1' in afile.classification['Measurement']:

                    safe = make_file_name_safe(afile.name, replace_str='_')
                    full_path = 'input/' + safe

                    while full_path in niftis:  # then repeated name
                        full_path = 'input/' + str(rpt) + '_' + safe
                        rpt += 1
                        
                    if os.path.isfile(full_path):
                        log.info('File exists ' + afile.name + ' -> ' +\
                             full_path + ' created ' + 
                             acquisition.original_timestamp.isoformat())
                    else:
                        log.info('Downloading ' + afile.name + ' -> ' +\
                             full_path + ' created ' + 
                             acquisition.original_timestamp.isoformat())
                        acquisition.download_file(afile.name, full_path)

                    niftis.append(full_path)

    context.gear_dict['niftis'] = niftis


def initialize(context):
    """Initialize logging and add informaiton to gear context:
        context.gear_dict:
            set COMMAND (only used here in log messages)
            initialize errors and warning lists
            set run_level
            set project, subject, and session information (id's labels and
                labels that can be used as file/folder names)
            set ouput file names and output_analysisid_dir
            set environ (system environment variables saved by Docker)
    Returns: logger
    """

    # Add manifest.json as the manifest_json attribute
    setattr(context, 'manifest_json', load_manifest_json())

    log = custom_log(context)

    context.log_config() # not configuring the log but logging the config

    # Instantiate custom gear dictionary to hold "gear global" info
    context.gear_dict = {}

    # get # cpu's to set -openmp
    cpu_count = str(os.cpu_count())
    log.info('psutil.cpu_count() = ' + cpu_count)
    context.gear_dict['cpu_count'] = cpu_count

    # The main command line command to be run (just command, no arguments):
    context.gear_dict['COMMAND'] = 'longitudinal'

    # Keep a list of errors and warning to print all in one place at end of log
    # Any errors will prevent the command from running and will cause exit(1)
    context.gear_dict['errors'] = []  
    context.gear_dict['warnings'] = []

    # Get level of run from destination's parent: subject or session
    fw = context.client
    dest_container = fw.get(context.destination['id'])
    context.gear_dict['run_level'] = dest_container.parent.type

    project_id = dest_container.parents.project
    context.gear_dict['project_id'] = project_id
    if project_id:
        project = fw.get(project_id)
        context.gear_dict['project_label'] = project.label
        context.gear_dict['project_label_safe'] = \
            make_file_name_safe(project.label, '_')
        log.info('Project label is "' + context.gear_dict['project_label'] +'"')
    else:
        context.gear_dict['project_label'] = 'unknown_project'
        context.gear_dict['project_label_safe'] = 'unknown_project'
        log.warning('Project label is ' + context.gear_dict['project_label'])

    subject_id = dest_container.parents.subject
    context.gear_dict['subject_id'] = subject_id
    if subject_id:
        subject = fw.get(subject_id)
        context.gear_dict['subject'] = subject
        context.gear_dict['subject_code'] = subject.code
        context.gear_dict['subject_code_safe'] = \
            make_file_name_safe(subject.code, '_')
        log.info('Subject code is "' + context.gear_dict['subject_code'] + '"')
    else:
        context.gear_dict['subject_code'] = 'unknown_subject'
        context.gear_dict['subject_code_safe'] = 'unknown_subject'
        log.warning('Subject code is ' + context.gear_dict['subject_code'])

    session_id = dest_container.parents.session
    context.gear_dict['session_id'] = session_id
    if session_id:
        session = fw.get(session_id)
        context.gear_dict['session_label'] = session.label
        context.gear_dict['session_label_safe'] = \
            make_file_name_safe(session.label, '_')
        log.info('Session label is "' + context.gear_dict['session_label'] +'"')
    else:
        context.gear_dict['session_label'] = 'unknown_session'
        context.gear_dict['session_label_safe'] = 'unknown_session'
        log.warning('Session label is ' + context.gear_dict['session_label'])

    # Set first part of result zip file names based on the above file safe names
    set_zip_head(context)

    # in the output/ directory, add extra analysis_id directory name for easy
    #  zipping of final outputs to return.
    context.gear_dict['output_analysisid_dir'] = \
        context.output_dir + '/' + context.destination['id'] + '/ABE4869g'

    # grab environment for gear
    with open('/tmp/gear_environ.json', 'r') as f:
        environ = json.load(f)
        environ['SUBJECTS_DIR'] = context.gear_dict['output_analysisid_dir']
        context.gear_dict['environ'] = environ

        # Add environment to log if debugging
        kv = ''
        for k, v in environ.items():
            kv += k + '=' + v + ' '
        log.debug('Environment: ' + kv)

    find_freesurfer_license(context, '/opt/freesurfer/license.txt')

    return log


def set_up_data(context, log):
    """Download scans to run on"""
    try:

        if context.gear_dict['run_level'] == 'project':

            msg = 'This gear must be run at the subject, '+\
                          'not project level'
            context.gear_dict['errors'].append(msg)
            raise Exception(msg)

        elif context.gear_dict['run_level'] == 'subject':

            subject_code = context.gear_dict['subject_code']
            log.info('Downloading scans for subject "' + subject_code + '"')

            # Grab all T1 nifti files for this subject
            download_files(context)

        elif context.gear_dict['run_level'] == 'session':

            msg = 'This gear must be run at the subject, '+\
                          'not session level'
            context.gear_dict['errors'].append(msg)
            raise Exception(msg)

        else:
            msg = 'This job is not being run at the project subject or session'\
                  ' level'
            raise TypeError(msg)

    except Exception as e:
        context.gear_dict['errors'].append(e)
        log.critical(e)
        log.exception('Error in input download and validation.')


def execute(context, log):
    """Run the Freesurfer Longitudinal Pipeline"""
    try:

        # Don't run if there were errors or if this is a dry run
        ok_to_run = True
        dry = False
        ret = []  # return codes from all runs
        return_code = 1  # assume the worst

        if len(context.gear_dict['errors']) > 0:
            ok_to_run = False
            ret.append(1)
            log.info('Commands were NOT run because of previous errors.')

        elif context.config['gear-dry-run']:
            dry = True
            e = 'gear-dry-run is set: Commands were NOT run.'
            log.warning(e)
            context.gear_dict['warnings'].append(e)
            utils.dry_run.pretend_it_ran(context)

        if ok_to_run:

            # Create output directory
            log.info('Creating ' + context.gear_dict['output_analysisid_dir'])
            out = context.gear_dict['output_analysisid_dir']
            if not os.path.exists(out):
                os.makedirs(out)

            # ---------------------------------- #
            # The longitudinal pipeline, huzzah! #
            # ---------------------------------- #

            options = ' -openmp ' + context.gear_dict['cpu_count'] # zoom zomm

            if '3T' in context.config:
                options += ' -3T'

            subjects_dir = '/opt/freesurfer/subjects/'
            output_dir = context.gear_dict['output_analysisid_dir']

            # first link averages
            fst_links_to_make = ["fsaverage", "lh.EC_average","rh.EC_average"]
            for fst in fst_links_to_make:
                targ = os.path.join(subjects_dir, fst)
                link = os.path.join(output_dir, fst)
                if not os.path.exists(link):
                    log.info('Linking ' + targ + ' -> ' + link)
                    os.symlink(os.path.join(subjects_dir, fst),
                               os.path.join(output_dir, fst))
                else:
                    log.info('Link exists ' + link)

            # Run cross-sectional analysis on each nifti
            scrnum = 1
            visit = 'W23'
            for nifti in context.gear_dict['niftis']:
                cmd = 'recon-all -s ' + "{:04d}-".format(scrnum) + visit + \
                      ' -i ' + nifti + ' -all -qcache' + options
                if dry:
                    log.info('Not running: ' + cmd)
                else:
                    log.info('Running: ' + cmd)
                    ret.append(utils.system.run(context, cmd))
                scrnum += 1

            # Create template
            scrnum = 1
            cmd = 'recon-all -base BASE '
            for nifti in context.gear_dict['niftis']:
                cmd += '-tp ' + "{:03d}".format(scrnum) + ' '
                scrnum += 1
            cmd += '-all' + options
            if dry:
                log.info('Not running: ' + cmd)
            else:
                log.info('Running: ' + cmd)
                ret.append(utils.system.run(context, cmd))

            # Run longitudinal on each time point
            scrnum = 1
            for nifti in context.gear_dict['niftis']:
                cmd = 'recon-all -long ' + "{:04d}-".format(scrnum) + visit + \
                      ' BASE -all' + options
                if dry:
                    log.info('Not running: ' + cmd)
                else:
                    log.info('Running: ' + cmd)
                    ret.append(utils.system.run(context, cmd))
                scrnum += 1

            # run asegstats2table and aparcstats2table to create tables from
            # aseg.stats and ?h.aparc.stats.  Then modify the results. 
            # abe_freesurfer_tables.pl
            os.chdir(out)
            cmd = '/flywheel/v0/abe_freesurfer_tables.pl .'
            log.info('Running: ' + cmd)
            ret.append(utils.system.run(context, cmd))

        log.info('Return codes: ' + repr(ret))

        if all(rr == 0 for rr in ret):
            log.info('Command successfully executed!')
            return_code = 0

        else:
            log.info('Command failed.')
            return_code = 1

    except Exception as e:
        context.gear_dict['errors'].append(e)
        log.critical(e)
        log.exception('Unable to execute command.')

    finally:

        # zip entire output/<analysis_id> folder
        zip_output(context)

        # clean up: remove output that was zipped (useful for testing)
        if os.path.exists(context.gear_dict['output_analysisid_dir']):
            if not context.config['gear-keep-output']:

                path = context.output_dir + '/' + context.destination['id']
                log.debug('removing output directory "' + path + '"')
                shutil.rmtree(path)

            else:
                log.info('NOT removing output directory "' + 
                          context.gear_dict['output_analysisid_dir'] + '"')

        else:
            log.info('Output directory does not exist so it cannot be removed')

        if len(context.gear_dict['warnings']) > 0 :
            msg = 'Previous warnings:\n'
            for err in context.gear_dict['warnings']:
                if str(type(err)).split("'")[1] == 'str':
                    # show string
                    msg += '  Warning: ' + str(err) + '\n'
                else:  # show type (of warning) and warning message
                    msg += '  ' + str(type(err)).split("'")[1] + ': ' + \
                           str(err) + '\n'
            log.info(msg)

        if len(context.gear_dict['errors']) > 0 :
            msg = 'Previous errors:\n'
            for err in context.gear_dict['errors']:
                if str(type(err)).split("'")[1] == 'str':
                    # show string
                    msg += '  Error msg: ' + str(err) + '\n'
                else:  # show type (of error) and error message
                    msg += '  ' + str(type(err)).split("'")[1] + ': ' + \
                           str(err) + '\n'
            log.info(msg)
            return_code = 1

        log.info('Gear is done.  Returning '+str(return_code))
        os.sys.exit(return_code)
 

if __name__ == '__main__':

    context = flywheel.GearContext()

    log = initialize(context)

    if len(context.gear_dict['errors']) == 0:
        set_up_data(context, log)

    execute(context, log)


# vi:set autoindent ts=4 sw=4 expandtab : See Vim, :help 'modeline'
