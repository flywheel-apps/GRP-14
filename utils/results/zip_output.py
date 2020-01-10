# If you edit this file, please consider updating bids-app-template

import os
import logging
from zipfile import ZipFile, ZIP_DEFLATED


log = logging.getLogger(__name__)


def zip_output(context):
    """Create zipped results"""


    # This executes regardless of errors or exit status,

    # Set Zip file "name": either project, subject, or session name
    if context.gear_dict['run_level'] == 'project':
        name = context.gear_dict['project_label_safe']

    elif context.gear_dict['run_level'] == 'subject':
        name = context.gear_dict['subject_code_safe']

    elif context.gear_dict['run_level'] == 'session':
        name = context.gear_dict['session_label_safe']

    analysis_id = context.destination['id']

    gear_name = context.manifest_json['name']
    file_name = gear_name + '_' + name + '_' + analysis_id + '.zip'

    dest_zip = os.path.join(context.output_dir,file_name)

    # The destination id is used as the subdirectory to put results into
    full_path = context.output_dir + '/' + context.destination['id']
    actual_dir = os.path.basename(full_path)

    if os.path.exists(full_path):

        log.debug('Output directory exists: ' + full_path)

        # output went into output/analysis_id/...
        os.chdir(context.output_dir)

        log.info(
            'Zipping ' + actual_dir + ' directory to ' + dest_zip + '.'
        )
        #command = ['zip', '-q', '-r', dest_zip, actual_dir]
        #result = sp.run(command, check=True)

        outzip = ZipFile(dest_zip, 'w', ZIP_DEFLATED)
        for root, _, files in os.walk(actual_dir):
            for fl in files:
                fl_path = os.path.join(root,fl)
                outzip.write(fl_path)
        outzip.close()

    else:

        log.error('Output directory does not exist: ' + full_path)

# vi:set autoindent ts=4 sw=4 expandtab : See Vim, :help 'modeline'
