#!/usr/bin/env python

import sys
import os
import argparse
import ConfigParser
import numpy as np
import psana
import time
import datetime

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='print slac psana event variables')
    parser.add_argument('config', type=str, \
                        help="file name of the configuration file")
    args = parser.parse_args()

    # check that args.ini exists
    if not os.path.exists(args.config):
        raise NameError('config file does not exist: ' + args.config)
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

def my_import(name):
    mod = __import__(name)
    components = name.split('.')
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

def my_psana_from_string(name):
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod
    #run_name = '0001'
    #ds = psana.DataSource('exp=cxig2614:run='+run_name+':idx')
    #ds = psana.DataSource('exp=cxif5315:run=139-152:idx')
    #ds = psana.DataSource('exp=cxig4415:run=23:idx')
    ds = psana.DataSource(source)

if __name__ == "__main__":
    args = parse_cmdline_args()
    
    config = ConfigParser.ConfigParser()
    config.read(args.config)
    
    params = parse_parameters(config)

    source = 'exp='+params['source']['exp']+':'+'run='+params['source']['runs']+':idx'

    print '\ndata source :', source

    print '\nOpening dataset...'
    ds = psana.DataSource(source)

    print '\nEpics pv Names (the confusing ones):'
    print ds.env().epicsStore().pvNames()


    print '\nEpics aliases (the not so confusing ones):'
    print ds.env().epicsStore().aliases()


    print '\nEvent structure:'
    itr = ds.events()
    evt = itr.next()
    for k in evt.keys():
        print 'type:', k.type(), 'source:', k.src(), 'alias:', k.alias(), 'key:', k.key()

    print '\n\n'
    for k in evt.keys():
        print k

    #beam = evt.get(psana.Bld.BldDataEBeamV7, psana.Source('BldInfo(EBeam)'))
    #print 'photon energy:', beam.ebeamPhotonEnergy()
