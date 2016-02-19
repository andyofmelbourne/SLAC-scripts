#!/usr/bin/env python

import sys
import os
import argparse
import ConfigParser
import numpy as np
#import psana
import time
import datetime

def parse_cmdline_args():
    parser = argparse.ArgumentParser(prog = 'run_stats.py', description='print slac run statistics (e.g. to put into a spreadsheet)')
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


if __name__ == "__main__":
    args = parse_cmdline_args()
    
    config = ConfigParser.ConfigParser()
    config.read(args.config)
    
    params = parse_parameters(config)

    source = 'exp='+params['source']['exp']+':'+'run='+params['source']['runs']+':idx'
    print source

    sys.exit()

    #source = 'exp=cxif5315:run='+runs+':idx'
    source = 'exp=cxi86715:run='+runs+':idx'
    print 'data source', source
    #run_name = '0001'
    #ds = psana.DataSource('exp=cxig2614:run='+run_name+':idx')
    #ds = psana.DataSource('exp=cxif5315:run=139-152:idx')
    #ds = psana.DataSource('exp=cxig4415:run=23:idx')
    ds = psana.DataSource(source)

    i = 0
    for run in ds.runs():
        times    = run.times()
        mylength = len(times)
        mytimes  = times[0:mylength]

        for i in range(1):
            evt = run.event(mytimes[i])
            evtId = evt.get(psana.EventId)
            run_length = len(times)
            #print run_length,zample_detector_encoded, '\t\t\t\t', evtId

            epics = ds.env().epicsStore()
            #zample_detector_encoded = epics.value('CXI:DS1:MMS:06.RBV') * 1.0e-3 + 0.5
            zample_detector_encoded = epics.value('CXI:DS2:MMS:06.RBV') * 1.0e-3 + 0.56

            pulse_length = epics.value('SIOC:SYS0:ML00:AO820')

            timestring = str(evtId).split('time=')[1].split(',')[0]
            timestamp = time.strptime(timestring[:-6],'%Y-%m-%d %H:%M:%S.%f')
            
            outputstr = []
            header = []

            if params['output']['id']:
                header.append('id')
                outputstr.append(str(evtId))

            if params['output']['events']:
                header.append('events')
                outputstr.append(str(run_length))

            if params['output']['z_stage']:
                header.append('z_stage')
                outputstr.append(str(zample_detector_encoded * 1.0e3))

            if params['output']['pulse_length']:
                header.append('pulse_length')
                outputstr.append(str(pulse_length))

            if params['output']['photon_energy']:
                header.append('photon_energy')
                try :
                    beam = evt.get(psana.Bld.BldDataEBeamV7, psana.Source('BldInfo(EBeam)'))
                    photon_energy_ev = beam.ebeamPhotonEnergy()
                    outputstr.append(str(photon_energy_ev * 1.0e-3))
                except :
                    print 'error extracting photon energy'

            if params['output']['seconds']:
                header.append('seconds')
                outputstr.append(str(mytimes[-1].seconds() - mytimes[0].seconds()))

            if params['output']['hms']:
                header.append('hms')
                outputstr.append( str(int((mytimes[-1].seconds() - mytimes[0].seconds())/3600.))+':'\
                      +str(int((mytimes[-1].seconds() - mytimes[0].seconds())/60.))+':'\
                      +str(int(mytimes[-1].seconds() - mytimes[0].seconds()) % 60))

            if params['output']['date']:
                header.append('date')
                outputstr.append( timestring[:10] )

            if params['output']['st']:
                header.append('st')
                outputstr.append( timestring[11:19] )

            if sys.argv[2] == 'id':
                print str(evtId)
            elif sys.argv[2] == 'l':
                print run_length

            elif sys.argv[2] == 'z':
                print zample_detector_encoded * 1.0e3
            elif sys.argv[2] == 'pl':
                print pulse_length
            elif sys.argv[2] == 'en':
                try :
                    beam = evt.get(psana.Bld.BldDataEBeamV7, psana.Source('BldInfo(EBeam)'))
                    photon_energy_ev = beam.ebeamPhotonEnergy()
                    print photon_energy_ev * 1.0e-3
                except :
                    print 'error extracting photon energy'
            elif sys.argv[2] == 'lt':
                print str(int((mytimes[-1].seconds() - mytimes[0].seconds())/3600.))+':'\
                      +str(int((mytimes[-1].seconds() - mytimes[0].seconds())/60.))+':'\
                      +str(int(mytimes[-1].seconds() - mytimes[0].seconds()) % 60)
            elif sys.argv[2] == 'ls':
                print (mytimes[-1].seconds() - mytimes[0].seconds())
            elif sys.argv[2] == 'date':
                print timestring[:10]
            elif sys.argv[2] == 'st':
                print timestring[11:19]
