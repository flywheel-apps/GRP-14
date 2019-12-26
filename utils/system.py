#!/usr/bin/env python3
"""System calls
"""

import logging
from subprocess import Popen, PIPE, STDOUT


log = logging.getLogger(__name__)


def run(context, command):
    """Execute a command line command using subprocess.Popen().  
    
    Why?  Because the version of python in the BIDS App Freesurfer container 
    is 3.4.

    Args:
        command (str): command line command to run
    """
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


# vi:set autoindent ts=4 sw=4 expandtab : See Vim, :help 'modeline'
