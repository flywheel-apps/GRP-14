import os
import logging
from pathlib import Path

import utils.system


log = logging.getLogger(__name__)


def pretend_it_ran(context):
    """
    Make some output like the command would have done only fake.
    """

    # Work diredtory
    path = 'work/'

    log.info('Creating fake output in ' + path)

    files = [path + 'somedir/d3.js',
             path + 'reportlets/somecmd/sub-TOME3024/anat/' + \
             'sub-TOME3024_desc-about_T1w.html']

    for ff in files:
        if os.path.exists(ff):
            log.debug('Exists: ' + ff)
        else:
            log.debug('Creating: ' + ff)
            dir_name = os.path.dirname(ff)
            os.makedirs(dir_name)
            Path(ff).touch(mode=0o777, exist_ok=True)

    # Output diredtory
    log.info('Creating fake output in ' + path)
    path = 'output/' + context.destination['id'] + '/'
    if os.path.exists(path):
        log.info('path already exists: ' + path)
    else:
        os.makedirs(path)
    os.chdir(path)
    cmd = 'tar zxf ../../dry_run_data.tgz'
    utils.system.run(context, cmd)
