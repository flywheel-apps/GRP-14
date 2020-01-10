"""
Installs Freesurfer license.txt file
"""

import os
import shutil
import logging


log = logging.getLogger(__name__)


def find_freesurfer_license(context, fs_license_path):
    """Creates the Freesurfer license file.

    The file is written at the provided path.  License text is found in one of
    3 ways and in this order:

    1) license.txt is provided as an input file,
    2) the text from license.txt is pasted into the "gear-FREESURFER_LICENSE"
       config, or
    3) the text from license.txt is pasted into a Flywheel project's "info" 
       metadata.

    See https://docs.flywheel.io/hc/en-us/articles/360013235453
    
    Args:
        context (flywheel.gear_context.GearContext): The gear context with core 
        functionality. Must have the 'gear_dict' attribute, and may have the
        'gear-FREESURFER_LICENSE' key/value in context.config.
        fs_license_path (str): The path to where the license should be insalled,
        $FREESURFER_HOME, e.g. "/opt/freesurfer/license.txt"
    """
    
    log.debug('')


    context.gear_dict['fs_license_found'] = False
    license_info = ''

    # 1) Check if the required FreeSurfer license file has been provided
    # as an input file.
    fs_license_file = context.get_input_path('freesurfer_license')

    if fs_license_file: # just copy the file to the right place

        fs_path_only, fs_file = os.path.split(fs_license_path)

        if fs_file != 'license.txt':
            log.warning('Freesurfer license file should be "license.txt", not'\
                        ' "' + fs_license_path + '"')

        if not os.path.exists(fs_path_only):
            os.makedirs(fs_path_only)
            log.warning('Had to make freesurfer license path: ' + \
                        fs_license_path)

        shutil.copy(fs_license_file, fs_license_path)

        context.gear_dict['fs_license_found'] = True
        log.info('Using FreeSurfer license in input file.')

    # 2) see if the license info was passed as a string argument
    if not context.gear_dict['fs_license_found']:

        if context.config.get('gear-FREESURFER_LICENSE'):

            fs_arg = context.config['gear-FREESURFER_LICENSE']
            license_info = '\n'.join(fs_arg.split())

            context.gear_dict['fs_license_found'] = True
            log.info('Using FreeSurfer license in gear argument.')

    # 3) see if the license info is in the project's info
    if not context.gear_dict['fs_license_found']:

        fw = context.client

        destination_id = context.destination.get('id')
        project_id = fw.get_analysis(destination_id).parents.project
        project = fw.get_project(project_id)

        if project.info.get('FREESURFER_LICENSE'):

            space_separated_text = project.info.get('FREESURFER_LICENSE')
            license_info = '\n'.join(space_separated_text.split())

            context.gear_dict['fs_license_found'] = True
            log.info('Using FreeSurfer license in project info.')

    if not context.gear_dict['fs_license_found']:
        msg = 'Could not find FreeSurfer license in project info.'
        log.exception(msg)
        os.sys.exit(1)

    else:
        # If it was passed as a string or was found in info, license_info is
        # set so save the Freesuefer license as a file in the right place.
        # If the license was an input file, it was copied to the right place
        # above (case 1).
        if license_info != '':

            head, tail = os.path.split(fs_license_path)

            if not os.path.exists(head):
                os.makedirs(head)

            with open(fs_license_path, 'w') as lf:
                lf.write(license_info)


# vi:set autoindent ts=4 sw=4 expandtab : See Vim, :help 'modeline'
