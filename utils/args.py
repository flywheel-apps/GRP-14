# If you edit this file, please consider updating bids-app-template

import subprocess as sp
import os, os.path as op
import logging
import re
import json

from .licenses.freesurfer import find_freesurfer_license


log = logging.getLogger(__name__)


def get_inputs_and_args(context):
    """
    Process inputs, contextual values and build a dictionary of
    key:value command-line parameter names:values These will be
    validated and assembled into a command-line below.  
    """

    log.debug('')

    # 1) Process Inputs

    # This is here because one way to pass the license is by an input
    find_freesurfer_license(context, '/opt/freesurfer/license.txt')

    # 2) Process Configuration (config, rest of command-line parameters)
    config = context.config
    params = {}
    for key in config.keys():
        if key[:5] == 'gear-':  # Skip any gear- parameters
            continue
        # Use only those boolean values that are True
        if type(config[key]) == bool:
            if config[key]:
                params[key] = True
            # else ignore (could this cause a problem?)
        else:
            if len(key) == 1:
                params[key] = config[key]
            else:
                if config[key] != 0:  # if zero, skip and use defaults
                    params[key] = config[key]
                # else ignore (could this caus a problem?)
    
    context.gear_dict['param_list'] =  params

    log.debug(repr(params))


def validate(context):
    """
    Validate settings of the Parameters constructed.
    Gives warnings for possible settings that could result in bad results.
    Gives errors (and raises exceptions) for settings that are violations 
    """


    param_list = context.gear_dict['param_list']

    log.debug('Checking param_list: ' + repr(param_list))

    I_must_not_go_on = False

    # all must be one of these strings
    if 'stages' in param_list:

        stages = param_list['stages'].split()

        for stage in stages:

            if stage not in ['autorecon1','autorecon2','autorecon2-cp',
                             'autorecon2-wm','autorecon-pial','autorecon3',
                             'autorecon-all','all']:
                msg = 'Invalid stage "' + stage + '"'
                context.gear_dict['errors'].append(msg)
                log.critical(msg)
                I_must_not_go_on = True

    # all must be one of these strings
    if 'steps' in param_list:

        steps = param_list['steps'].split()

        for step in steps:

            if step not in ['cross-sectional','template','longitudinal']:
                msg = 'Invalid step "' + step + '"'
                context.gear_dict['errors'].append(msg)
                log.critical(msg)
                I_must_not_go_on = True

    # all must be one of these strings
    if 'parcellations' in param_list:

        parcellations = param_list['parcellations'].split()

        for parc in parcellations:

            if parc not in ['aparc','aparc.a2009s']:
                msg = 'Invalid parc "' + parc + '"'
                context.gear_dict['errors'].append(msg)
                log.critical(msg)
                I_must_not_go_on = True

    # all must be one of these strings
    if 'measurements' in param_list:

        measurements = param_list['measurements'].split()

        for measure in measurements:

            if measure not in ['area','volume','thickness','thicknessstd',
                               'meancurv','gauscurv','foldind','curvind']:
                msg = 'Invalid measure "' + measure + '"'
                context.gear_dict['errors'].append(msg)
                log.critical(msg)
                I_must_not_go_on = True

    if I_must_not_go_on:
        log.exception('Configuration error.')
        raise Exception('Configuration error.')


def build_command(context):
    """
    command is a list of prepared commands
    param_list is a dictionary of key:value pairs to be put into the command list
    as such ("-k value" or "--key=value")
    """

    log.debug('')

    command = context.gear_dict['command_line']

    param_list = context.gear_dict['param_list']

    for key in param_list.keys():
        # Single character command-line parameters are preceded by a single '-'
        if len(key) == 1:
            command.append('-' + key)
            if len(str(param_list[key])) != 0:
                # append it like '-k value'
                command.append(str(param_list[key]))
        # Multi-Character command-line parameters are preceded by a double '--'
        else:
            # If Param is boolean and true include, else exclude
            if type(param_list[key]) == bool:
                if param_list[key]:
                    command.append('--' + key)
            else:
                # If Param not boolean, but without value include without value
                if len(str(param_list[key])) == 0:
                    # append it like '--key'
                    command.append('--' + key)
                else:
                    # check for argparse nargs='*' lists of multiple values so
                    #  append it like '--key val1 val2 ...'
                    if (isinstance(param_list[key], str) and len(param_list[key].split()) > 1):
                    # then it is a list of multiple things: e.g. "--modality T1w T2w"
                        command.append('--' + key)
                        for item in param_list[key].split():
                            command.append(item)
                    else: # single value so append it like '--key=value'
                        command.append('--' + key + '=' + str(param_list[key]))
        if key == 'verbose':
            # handle a 'count' argparse argument where manifest gives
            # enumerated possibilities like v, vv, or vvv
            # e.g. replace "--verbose=vvv' with '-vvv'
            command[-1] = '-' + param_list[key]


# vi:set autoindent ts=4 sw=4 expandtab : See Vim, :help 'modeline'
