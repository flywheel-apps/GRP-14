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

Summary Outputs (produced by freesurfer_tables.pl)
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
import re
import glob

import flywheel

from utils.license.freesurfer import find_freesurfer_license

from utils.fly.custom_log import custom_log
from utils.fly.load_manifest_json import load_manifest_json
from utils.fly.make_file_name_safe import make_file_name_safe

from utils.results.set_zip_name import set_zip_head
from utils.results.zip_output import zip_output

import utils.dry_run

import utils.system


def download_it(fw, acquisition, file_name, input_path):
    """Once proper file has been found, get it.

    Args:
        acquisition
        file_name
        input_path
    """

    safe = make_file_name_safe(file_name, replace_str='_')

    full_path = input_path + safe

    if acquisition.timestamp:
        if acquisition.timezone:
            created = acquisition.original_timestamp.isoformat()
        else:
            created = acquisition.timestamp.isoformat()
    else:
        created = 'unknown'

    rpt = 1
    while full_path in context.gear_dict['niftis']:  # then repeated name
        full_path = input_path + str(rpt) + '_' + safe
        rpt += 1

    if os.path.isfile(full_path):
        log.info('File exists ' + file_name + ' -> ' +\
             full_path + ' created ' + created)
    else:
        log.info('Downloading ' + file_name + ' -> ' +\
             full_path + ' created ' + created)
        acquisition.download_file(file_name, full_path)

    full_file = fw.get_acquisition_file_info(acquisition.id, file_name)
    field_strength = full_file.info.get('MagneticFieldStrength')

    context.gear_dict['niftis'].append(full_path)
    context.gear_dict['file_names'].append(file_name)
    context.gear_dict['createds'].append(created)
    context.gear_dict['field_strength'].append(field_strength)

def find_and_download_files(context):
    """Find apropriate files for the subject and download them

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


    input_path = 'input/'
    if os.path.isdir(input_path):
        log.debug('Path already exists: ' + input_path)
    else:
        log.debug('Creating: ' + input_path)
        os.mkdir(input_path)

    fw = context.client

    if 'classification_measurement' in context.config:
        class_meas = context.config['classification_measurement'].split()
    else:
        class_meas = ['T1']

    # session and acquisition include/exclude lists can come from:
    #   project info metadata,
    #   subject info metadata, and
    #   config options
    # The last one wins (how about getting it from an input file also, eh?)
    ses_exclude_list = None
    ses_include_list = None
    acq_exclude_list = None
    acq_include_list = None

    fs = 'freesurfer_longitudinal_'
    where = 'Found in project info'
    # check for exclude/include lists of regexs for sessions in project info
    sel = context.gear_dict['project'].info.get(fs + 'session_excludelist')
    if sel:
        ses_exclude_list = sel.split()
        log.info(where+' '+fs+'session_excludelist: "'+sel+'"')
    sil = context.gear_dict['project'].info.get(fs + 'session_includelist')
    if sil:
        ses_include_list = sil.split()
        log.info(where+' '+fs+'session_includelist: "'+sil+'"')
    # check for exclude/include lists of regexs for acquisitions in project info
    ael = context.gear_dict['project'].info.get(fs + 'acquisition_excludelist')
    if ael:
        acq_exclude_list = ael.split()
        log.info(where+' '+fs+'acquisition_excludelist: "'+ael+'"')
    ail = context.gear_dict['project'].info.get(fs + 'acquisition_includelist')
    if ail:
        acq_include_list = ail.split()
        log.info(where+' '+fs+'acquisition_includelist: "'+ail+'"')

    where = 'Found in subject info'
    # check for exclude/include lists of regexs for sessions in subject info
    sel = context.gear_dict['subject'].info.get(fs + 'session_excludelist')
    if sel:
        ses_exclude_list = sel.split()
        log.info(where+' '+fs+'session_excludelist: "'+sel+'"')
    sil = context.gear_dict['subject'].info.get(fs + 'session_includelist')
    if sil:
        ses_include_list = sil.split()
        log.info(where+' '+fs+'session_includelist: "'+sil+'"')
    # check for exclude/include lists of regexs for acquisitions in subject info
    ael = context.gear_dict['subject'].info.get(fs + 'acquisition_excludelist')
    if ael:
        acq_exclude_list = ael.split()
        log.info(where+' '+fs+'acquisition_excludelist: "'+ael+'"')
    ail = context.gear_dict['subject'].info.get(fs + 'acquisition_includelist')
    if ail:
        acq_include_list = ail.split()
        log.info(where+' '+fs+'acquisition_includelist: "'+ail+'"')

    where = 'Found in config'
    # set up exclude/include lists of reegexs for sessions in config
    if 'session_excludelist' in context.config:
        ses_exclude_list = context.config['session_excludelist'].split()
        log.info(where+' session_excludelist: "'+str(ses_exclude_list)+'"')
    if 'session_includelist' in context.config:
        ses_include_list = context.config['session_includelist'].split()
        log.info(where+' session_includelist: "'+str(ses_include_list)+'"')

    # set up exclude/include lists of reegexs for acquisitions in config
    if 'acquisition_excludelist' in context.config:
        acq_exclude_list = context.config['acquisition_excludelist'].split()
        log.info(where+' acquisition_excludelist: "'+str(acq_exclude_list)+'"')
    if 'acquisition_includelist' in context.config:
        acq_include_list = context.config['acquisition_includelist'].split()
        log.info(where+' acquisition_includelist: "'+str(acq_include_list)+'"')

    # go through all sessions, acquisitions to find files
    for session in context.gear_dict['subject'].sessions():

        lemme_out = False
        if ses_exclude_list:
            for regex in ses_exclude_list:
                if re.search(regex, session.label):  # if excluded, skip
                    log.info('Session "' + session.label + '" matches ' + \
                             'exclusion regex, skipping it')
                    lemme_out = True
                    continue
        if lemme_out:
            continue

        if ses_include_list:
            match = False
            for regex in ses_include_list:
                if not re.search(regex, session.label):
                    match = True
            if match:
                continue  # if  not included (matches any regex), skip
            else:
                log.info('Session "' + session.label + '" matches ' \
                         'an inclusion regex, keeping it')

        for acquisition in fw.get_session_acquisitions(session.id):

            lemme_out = False
            if acq_exclude_list:
                for regex in acq_exclude_list:
                    if re.search(regex, acquisition.label):  # if excluded, skip
                        log.info('Acquisition "' + acquisition.label + \
                                 '" matches exclusion regex, skipping it')
                        lemme_out = True
                        continue
            if lemme_out:
                continue

            if acq_include_list:
                match = False
                for regex in acq_include_list:
                    if not re.search(regex, acquisition.label):
                        match = True
                if match:
                    continue  # if  not included (matches any regex), skip
                else:
                    log.info('Acquisition "' + acquisition.label + '" ' + \
                             'matches an inclusion regex, keeping it')

            for afile in acquisition.files:

                # Scan must be nifti
                if afile.type == 'nifti':

                    found_one = False
                    for cm in class_meas:
                        if 'Measurement' in afile.classification:
                            if cm in afile.classification['Measurement']:
                                found_one = True
                                log.info('Found ' + cm + ' file')

                    if found_one:
                        download_it(fw, acquisition, afile.name, input_path)
                        context.gear_dict['visits'].append(
                            make_file_name_safe(session.label, '_'))
                    else:
                        log.info('Ignoring ' + afile.name)


def update_gear_status(key, value):
    """Set destination's 'info' to indicate what's happening"""

    fw = context.client
    dest_container = fw.get(context.destination['id'])
    kwargs = {key: value}
    dest_container.update_info(kwargs)
    log.info(repr(kwargs))


def set_recon_all_status(subject_dir):
    """Set final status to last line of recon-all-status.log."""

    path = context.gear_dict['output_analysisid_dir'] + '/' + \
           subject_dir + '/scripts/recon-all-status.log'
    if os.path.exists(path):
        with open(path, 'r') as fh:
            for line in fh:
                pass
            last_line = line
    else:
        last_line = 'recon-all-status.log is missing'
    update_gear_status(subject_dir, last_line)

def update_gear_status(key, value):
    """Set destination's 'info' to indicate what's happening"""

    fw = context.client
    dest_container = fw.get(context.destination['id'])
    kwargs = {key: value}
    dest_container.update_info(kwargs)
    log.info(repr(kwargs))


def set_recon_all_status(subject_dir):
    """Set final status to last line of recon-all-status.log."""

    path = context.gear_dict['output_analysisid_dir'] + '/' + \
           subject_dir + '/scripts/recon-all-status.log'
    if os.path.exists(path):
        with open(path, 'r') as fh:
            for line in fh:
                pass
            last_line = line
    else:
        last_line = 'recon-all-status.log is missing'
    update_gear_status(subject_dir, last_line)

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

    # These lists will have the same number of elements so the ith 
    # elements in each refer to the same file/acquisition.
    context.gear_dict['niftis'] = []
    context.gear_dict['file_names'] = []
    context.gear_dict['createds'] = []
    context.gear_dict['visits'] = []
    context.gear_dict['field_strength'] = []

    # get # cpu's to set -openmp
    cpu_count = os.cpu_count()
    str_cpu_count = str(cpu_count)
    log.info('os.cpu_count() = ' + str_cpu_count)
    if 'n_cpus' in context.config:
        if context.config['n_cpus'] < 1:
            log.warning('n_cpus < 1, using 1')
            cpu_count = 1
            str_cpu_count = str(cpu_count)
        elif context.config['n_cpus'] <= cpu_count:
            cpu_count = context.config['n_cpus']
            str_cpu_count = str(cpu_count)
            log.info('using n_cpus = ' + str_cpu_count)
        else:
            log.warning('n_cpus ' + str(context.config["n_cpus"]) + ' > ' + \
                         'os.cpu_count(), using ' + str_cpu_count)
    context.gear_dict['cpu_count'] = str_cpu_count

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
        context.gear_dict['project'] = project
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
        context.output_dir + '/' + context.destination['id'] + '/' + \
        context.gear_dict['project_label_safe']

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
            find_and_download_files(context)

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


def field_strength_close_enough(field_strength, desired_value):
    """Check if the ginve value is "close enough" to the desired value
    
    Because sometimes MagneticFieldStrength can be provide in mT (3000, 1500) 
    or something like 2.9721T
    
    Args:
        field_strength (float): DICOM MagneticFieldStrength value
        desired_value (float): value in Teslas to compare with, e.g. 3
            as opposed to 1.5.
    """

    if field_strength > 100:  # assume it is in mT instead of Teslas
        field_strength /= 1000  # and turn it into Teslas

    diff = abs(field_strength - desired_value)

    if diff < 0.2:
        return True
    else:
        return False


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
            # study is freesurfer's SUBJECTS_DIR
            scrnum = context.gear_dict['subject_code_safe']
            num_niftis = str(len(context.gear_dict['niftis']))

            for nn, nifti in enumerate(context.gear_dict['niftis']):

                if field_strength_close_enough(
                    context.gear_dict['field_strength'][nn], 3):
                        if ' -3T' not in options:
                            options += ' -3T'

                subject_dir = scrnum + "-" + context.gear_dict['visits'][nn]

                update_gear_status('longitudinal-step', 'cross-sectional ' + \
                    subject_dir + ' (' + str(nn + 1) + ' of ' + num_niftis + \
                    ') "' + context.gear_dict['file_names'][nn] + '" ' + \
                    context.gear_dict['createds'][nn])

                cmd = 'recon-all -s ' + subject_dir + \
                      ' -i ' + nifti + ' -all -qcache' + options
                if dry:
                    log.info('Not running: ' + cmd)
                else:
                    log.info('Running: ' + cmd)
                    ret.append(utils.system.run(context, cmd))

                set_recon_all_status(subject_dir)

                set_recon_all_status(subject_dir)

            # Create template
            cmd = 'recon-all -base BASE '

            update_gear_status('longitudinal-step', 'Create template')

            for nn, nifti in enumerate(context.gear_dict['niftis']):

                subject_dir = scrnum + "-" + context.gear_dict['visits'][nn]

                cmd += '-tp ' + subject_dir + ' '

            cmd += '-all' + options
            if dry:
                log.info('Not running: ' + cmd)
            else:
                log.info('Running: ' + cmd)
                ret.append(utils.system.run(context, cmd))

            set_recon_all_status('BASE')

            # Run longitudinal on each time point

            for nn, nifti in enumerate(context.gear_dict['niftis']):

                subject_dir = scrnum + "-" + context.gear_dict['visits'][nn]

                update_gear_status('longitudinal-step', 'longitudinal ' +
                    subject_dir + ' (' + str(nn + 1) + ' of ' + num_niftis + \
                    ') "' + context.gear_dict['file_names'][nn] + '" ' + \
                    context.gear_dict['createds'][nn])

                cmd = 'recon-all -long ' + subject_dir + ' BASE -all' + options
                if dry:
                    log.info('Not running: ' + cmd)
                else:
                    log.info('Running: ' + cmd)
                    ret.append(utils.system.run(context, cmd))

                set_recon_all_status(subject_dir + '.long.BASE')

            update_gear_status('longitudinal-step', 'all steps completed')

            # run asegstats2table and aparcstats2table to create tables from
            # aseg.stats and ?h.aparc.stats.  Then modify the results.
            # freesurfer_tables.pl
            os.chdir(out)
            cmd = '/flywheel/v0/freesurfer_tables.pl .'
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

        # Copy summary csv files to top-level output
        files = glob.glob(context.gear_dict['output_analysisid_dir'] + \
                         '/tables/*')
        for ff in files:
            shutil.copy(ff,context.output_dir)

        if context.config['remove_subjects_dir']:
            # Remove all of Freesurfer's subject  directories
            paths = glob.glob(context.gear_dict['output_analysisid_dir'] + '/*')
            for path in paths:
                if os.path.basename(path) != 'tables':
                    if os.path.islink(path):
                        os.unlink(path)
                        log.debug('removing link "' + path + '"')
                    elif os.path.isdir(path):
                        log.debug('removing subject directory "' + path + '"')
                        shutil.rmtree(path)

        # Default config: zip entire output/<analysis_id> folder
        if os.path.exists(context.gear_dict['output_analysisid_dir']):
            if context.config['gear-zip-output']:

                zip_output(context)

                path = context.output_dir + '/' + context.destination['id']
                log.debug('removing output directory "' + path + '"')
                shutil.rmtree(path)

            else:
                log.info('NOT zipping output directory "' +
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
