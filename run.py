#!/usr/bin/env python3
""" Run the gear: set up for and call command-line code """

import os
from subprocess import Popen, PIPE, STDOUT
import sys
import logging
import shutil

import flywheel

from utils import args

from utils.dicom.import_dicom_header_as_dict import *

from utils.fly.custom_log import *
from utils.fly.load_manifest_json import *
from utils.fly.make_file_name_safe import *

from utils.results.set_zip_name import set_zip_head

import utils.dry_run


def run(command):
    log.info('Running: ' + command)
    ignore_errors=False
    process = Popen(command, stdout=PIPE, stderr=STDOUT, shell=True, 
                    env=context.gear_dict['environ'])
    while True:
        line = process.stdout.readline()
        line = str(line, 'utf-8')[:-1]
        print(line)
        if line == '' and process.poll() is not None:
            break
    if process.returncode != 0 and not ignore_errors:
        raise Exception("Non zero return code: %d" % process.returncode)

    return process.returncode


def initialize(context):

    # Add manifest.json as the manifest_json attribute
    setattr(context, 'manifest_json', load_manifest_json())

    log = custom_log(context)

    context.log_config() # not configuring the log but logging the config

    # Instantiate custom gear dictionary to hold "gear global" info
    context.gear_dict = {}

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
    else:
        context.gear_dict['project_label'] = 'unknown_project'
        context.gear_dict['project_label_safe'] = 'unknown_project'
        log.warning('Project label is ' + context.gear_dict['project_label'])

    subject_id = dest_container.parents.subject
    context.gear_dict['subject_id'] = subject_id
    if subject_id:
        subject = fw.get(subject_id)
        context.gear_dict['subject_code'] = subject.code
        context.gear_dict['subject_code_safe'] = \
            make_file_name_safe(subject.code, '_')
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
    else:
        context.gear_dict['session_label'] = 'unknown_session'
        context.gear_dict['session_label_safe'] = 'unknown_session'
        log.warning('Session label is ' + context.gear_dict['session_label'])

    # Set first part of result zip file names based on the above file safe names
    set_zip_head(context)

    # in the output/ directory, add extra analysis_id directory name for easy
    #  zipping of final outputs to return.
    context.gear_dict['output_analysisid_dir'] = \
        context.output_dir + '/' + context.destination['id'] + '/subjects'

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

    return log


def create_command(context, log):

    # Create the command and validate the given arguments
    try:

        # Set the actual gear command:
        command = [context.gear_dict['COMMAND']]

        # positional args: output dir, analysis level
        # This should be done here in case there are nargs='*' arguments
        command.append(context.gear_dict['output_analysisid_dir'])

        # Put command into gear_dict so arguments can be added in args.
        context.gear_dict['command_line'] = command

        # Process inputs, contextual values and build a dictionary of
        # key-value arguments specific for COMMAND
        args.get_inputs_and_args(context)

        # Validate the command parameter dictionary - make sure everything is 
        # ready to run so errors will appear before launching the actual gear 
        # code.  Raises Exception on fail
        args.validate(context)

        # Build final command-line (a list of strings)
        # result is put into context.gear_dict['command_line'] 
        args.build_command(context)

    except Exception as e:
        context.gear_dict['errors'].append(e)
        log.critical(e)
        log.exception('Error in creating and validating command.')


def set_up_data(context, log):
    # Set up and validate data to be used by command
    try:


        if context.gear_dict['run_level'] == 'project':

            msg = 'This gear must be run at the subject, '+\
                          'not project level'
            context.gear_dict['errors'].append(msg)
            raise Exception(msg)

        elif context.gear_dict['run_level'] == 'subject':

            subject_code = context.gear_dict['subject_code']
            log.info('Downloading scans for subject "' + subject_code + '"')

            niftis = []
            fw = context.client
            project_sessions = \
                fw.get_project_sessions(context.gear_dict['project_id'])
            for session in project_sessions:
                if session['subject']['code'] == subject_code:
                    acquisitions = fw.get_session_acquisitions(session.id)
                    for acquisition in acquisitions:
                        for afile in acquisition.files:
                            full_path = 'input/' + afile.name
                            if os.path.isfile(full_path):
                                log.info('File exists ' + afile.name)
                            else:
                                log.info('Downloading ' + afile.name)
                                acquisition.download_file(afile.name, full_path)
                            niftis.append(full_path)

            context.gear_dict['niftis'] = niftis

        elif context.gear_dict['run_level'] == 'session':

            msg = 'This gear must be run at the subject, '+\
                          'not session level'
            context.gear_dict['errors'].append(msg)
            raise Exception(msg)

        else:
            msg = 'This job is not being run at the project subject or session level'
            raise TypeError(msg)

    except Exception as e:
        context.gear_dict['errors'].append(e)
        log.critical(e)
        log.exception('Error in input download and validation.')


def execute(context, log):
    try:

        # Don't run if there were errors or if this is a dry run
        ok_to_run = True

        if len(context.gear_dict['errors']) > 0:
            ok_to_run = False
            result = sp.CompletedProcess
            ret = 1
            log.info('Command was NOT run because of previous errors.')

        elif context.config['gear-dry-run']:
            ok_to_run = False
            result = sp.CompletedProcess
            ret = 0
            e = 'gear-dry-run is set: Command was NOT run.'
            log.warning(e)
            context.gear_dict['warnings'].append(e)
            utils.dry_run.pretend_it_ran(context)

        ret = 1 # assume the worst
        if ok_to_run:

            # Create output directory
            log.info('Creating ' + context.gear_dict['output_analysisid_dir'])
            out = context.gear_dict['output_analysisid_dir']
            if not os.path.exists(out):
                os.makedirs(out)

            # ------------------------- #
            # The longitudinal pipeline #
            # ------------------------- #
            dry = False
            dry = True

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
            vid = 1
            for nifti in context.gear_dict['niftis']:
                cmd = 'recon-all -s ' + str(vid) + ' -i ' + nifti +\
                      ' -all -qcache '
                if dry:
                    print('Not running: ' + cmd)
                    ret = 0
                else:
                    ret = run(cmd)
                vid += 1

            # Create template
            vid = 1
            cmd = 'recon-all -base BASE '
            for nifti in context.gear_dict['niftis']:
                cmd += '-tp ' + str(vid) + ' '
                vid += 1
            cmd += '-all -qcache '
            if dry:
                print('Not running: ' + cmd)
                ret = 0
            else:
                ret = run(cmd)

            # Run longitudinal on each time point
            vid = 1
            for nifti in context.gear_dict['niftis']:
                cmd = 'recon-all -long ' + str(vid) + ' BASE -all -qcache'
                if dry:
                    print('Not running: ' + cmd)
                    ret = 0
                else:
                    ret = run(cmd)
                vid += 1

        log.info('Return code: ' + str(ret))

        if ret == 0:
            log.info('Command successfully executed!')

        else:
            log.info('Command failed.')

    except Exception as e:
        context.gear_dict['errors'].append(e)
        log.critical(e)
        log.exception('Unable to execute command.')

    finally:

        if False:
            # zip entire output/<analysis_id> folder
            zip_output(context)

            # possibly save ALL intermediate output
            if context.config['gear-save-intermediate-output']:
                zip_all_intermediate_output(context)

            # possibly save intermediate files and folders
            zip_intermediate_selected(context)

            # clean up: remove output that was zipped
            if os.path.exists(context.gear_dict['output_analysisid_dir']):
                if not context.config['gear-keep-output']:

                    shutil.rmtree(context.gear_dict['output_analysisid_dir'])
                    log.debug('removing output directory "' + 
                              context.gear_dict['output_analysisid_dir'] + '"')

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
                    msg += '  ' + str(type(err)).split("'")[1] + ': ' + str(err) + '\n'
            log.info(msg)

        if len(context.gear_dict['errors']) > 0 :
            msg = 'Previous errors:\n'
            for err in context.gear_dict['errors']:
                if str(type(err)).split("'")[1] == 'str':
                    # show string
                    msg += '  Error msg: ' + str(err) + '\n'
                else:  # show type (of error) and error message
                    msg += '  ' + str(type(err)).split("'")[1] + ': ' + str(err) + '\n'
            log.info(msg)
            ret = 1

        log.info('Gear is done.  Returning '+str(ret))
        os.sys.exit(ret)
 

if __name__ == '__main__':

    context = flywheel.GearContext()

    log = initialize(context)

    create_command(context, log)

    if len(context.gear_dict['errors']) == 0:
        set_up_data(context, log)

    execute(context, log)


# vi:set autoindent ts=4 sw=4 expandtab : See Vim, :help 'modeline'
