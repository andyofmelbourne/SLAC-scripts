#!/usr/bin/env python

import sys
import os
import argparse
import ConfigParser
import numpy as np
import time
import datetime

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='write laser off calibration for xtcav to calib')
    parser.add_argument('-c', '--config', type=str, \
                        help="file name of the configuration file")
    parser.add_argument('-e', '--experiment', type=str, \
                help="psana experiment string (e.g cxi01516)")
    parser.add_argument('-r', '--run', type=str, \
                help="experiment run/s (e.g 101 or 101-110)")
    parser.add_argument('-m', '--maxshots', type=int, \
                default = 1000, \
                help="maximum number of frames to process (e.g 5000)")
    parser.add_argument('-o', '--output', type=int, \
                default = None, \
                help="output directory for the psana calib files (by default this goes into the experiment calib)")
    parser.add_argument('-b', '--bunches', type=int, \
                default = 1, \
                help="number of xray bunches in each frame (e.g 1 or 2)")
    args = parser.parse_args()

    # check that args.ini exists
    if args.config is not None :
        if not os.path.exists(args.config):
            raise NameError('config file does not exist: ' + args.config)
    elif args.experiment is None :
        raise NameError('must set --experiment or supply a config file.')

    if args.config is not None :
        config = ConfigParser.ConfigParser()
        config.read(args.config)
        params = parse_parameters(config)
        
        args.experiment = str(params['source']['exp'])
        args.run        = str(params['source']['run'])
        args.maxshots   = params['params']['maxshots']
        args.output     = params['params']['output']
        args.bunches  = params['params']['bunches']

    return args


def parse_parameters(config):
    """
    Parse values from the configuration file and sets internal parameter accordingly
    The parameter dictionary is made available to both the workers and the master nodes
    The parser tries to interpret an entry in the configuration file as follows:
    - If the entry starts and ends with a single quote, it is interpreted as a string
    - If the entry is the word None, without quotes, then the entry is interpreted as NoneType
    - If the entry is the word False, without quotes, then the entry is interpreted as a boolean False
    - If the entry is the word True, without quotes, then the entry is interpreted as a boolean True
    - If non of the previous options match the content of the entry, the parser tries to interpret the entry in order as:
        - An integer number
        - A float number
        - A string
      The first choice that succeeds determines the entry type
    """

    monitor_params = {}

    for sect in config.sections():
        monitor_params[sect]={}
        for op in config.options(sect):
            monitor_params[sect][op] = config.get(sect, op)
            if monitor_params[sect][op].startswith("'") and monitor_params[sect][op].endswith("'"):
                monitor_params[sect][op] = monitor_params[sect][op][1:-1]
                continue
            if monitor_params[sect][op] == 'None':
                monitor_params[sect][op] = None
                continue
            if monitor_params[sect][op] == 'False':
                monitor_params[sect][op] = False
                continue
            if monitor_params[sect][op] == 'True':
                monitor_params[sect][op] = True
                continue
            try:
                monitor_params[sect][op] = int(monitor_params[sect][op])
                continue
            except :
                try :
                    monitor_params[sect][op] = float(monitor_params[sect][op])
                    continue
                except :
                    # attempt to pass as an array of ints e.g. '1, 2, 3'
                    try :
                        l = monitor_params[sect][op].split(',')
                        monitor_params[sect][op] = np.array(l, dtype=np.int)
                        continue
                    except :
                        pass

    return monitor_params


def laserOffReference(args):
    import psana
    
    # The calib line below will write the calib directory in the current directory
    # For 'real' analysis during the beamtime just delete it and the calib directory
    # for the experiment will be used by default.
    if args.output is not None :
        psana.setOption('psana.calib-dir','calib')
    
    from xtcav.GenerateLasingOffReference import *
    GLOC=GenerateLasingOffReference();
    GLOC.experiment='xpptut15'
    GLOC.runs=args.run
    GLOC.maxshots=args.maxshots
    GLOC.nb=args.bunches
    GLOC.islandsplitmethod = 'scipyLabel'       # see confluence documentation for how to set this parameter
    GLOC.groupsize=1                            # see confluence documentation for how to set this parameter
    GLOC.SetValidityRange(int(args.run))        # delete second run number argument to have the validity range be open-ended ("end")
    GLOC.Generate();

if __name__ == '__main__':
    args = parse_cmdline_args()
    laserOffReference(args)
    
