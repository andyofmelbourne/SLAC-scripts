#!/usr/bin/env python

import sys
import os
import argparse
import ConfigParser
import numpy as np
import time
import datetime

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='Get the xray power vs time profile for every shot')
    parser.add_argument('-c', '--config', type=str, \
                        help="file name of the configuration file")
    parser.add_argument('-e', '--experiment', type=str, \
                help="psana experiment string (e.g cxi01516)")
    parser.add_argument('-r', '--run', type=str, \
                help="experiment run/s (e.g 101 or 101-110)")
    parser.add_argument('-m', '--mode', type=str, \
                default = '', \
                help="psana access mode (smd for semi-online)")
    parser.add_argument('-d', '--h5dir', type=str, \
                default = '', \
                help="output director for the h5 file.")
    parser.add_argument('-f', '--h5fnam', type=str, \
                default = 'exp-run-xtcav-powerstack.h5', \
                help="output file name for the h5 file.")
    parser.add_argument('--matchfnam', type=bool, \
                default = True, \
                help="use regular expression to match 'exp' and 'run' in the filename.")
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
        args.mode       = params['params']['mode']
        args.bunches    = params['params']['bunches']
        args.h5dir      = params['output']['h5dir']
        args.h5fnam     = params['output']['h5fnam']
        args.matchfnam  = params['output']['matchfnam']
        args.calib      = params['params']['calib']
        args.chunksize  = params['params']['chunksize']

    import string
    if args.matchfnam :
        args.h5fnam = string.replace(args.h5fnam, 'exp', args.experiment)
        args.h5fnam = string.replace(args.h5fnam, 'run', 'r' + str(args.run).zfill(4))

    if args.mode != '' and args.mode[0] != ':' :
        args.mode = ':' + args.mode

    args.source = 'exp='+args.experiment+':'+'run='+str(args.run)+args.mode

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


def write_h5(fnam, path, index, data):
    f = h5py.File(fnam, 'a')
    try :
        dset = f[path]
        dset.resize(index + data.shape[0], axis = 0)
    except Exception as e :
        dset = f.create_dataset(path, data.shape, maxshape = (None,) + data[0].shape, dtype=data.dtype)

    dset[index : index + data.shape[0]] = data 
    f.close()


def collect(data):
    if rank == 0 :
        data_rec = [data.copy()]
        for i in range(1, size):
            #print 'gathering data from rank:', i
            data_rec.append( comm.recv(source = i, tag = i) )
        data = np.array([e for es in data_rec for e in es])
    else :
        comm.send(data, dest=0, tag=rank)
    return data


def collect_and_write(fnam, processed_events, chunksize, stuff):
    stuff_tot  = []
    stuff_tot.append(collect(stuff[0][1]))
    
    if rank == 0 :
        j = np.argsort(stuff_tot[0])
    
    for v in stuff[1:]:
        stuff_tot.append(collect(v[1]))

    # write to file
    if rank == 0 :
        for i in range(len(stuff)):
            write_h5(fnam, stuff[i][0], processed_events, stuff_tot[i][j])

if __name__ == "__main__":
    args = parse_cmdline_args()
    
    import psana
    import h5py
    import xtcav.ShotToShotCharacterization
    
    if args.calib is not None :
        print 'loading psana calib dir:', args.calib
        psana.setOptions( { 'psana.calib-dir' : args.calib, 'psana.allow-corrupt-epics' : True } )

    print 'sourcing:', args.source
    ds = psana.DataSource(args.source)

    #XTCAV Retrieval (setting the data source is useful to get information such as experiment name)
    XTCAVRetrieval = xtcav.ShotToShotCharacterization.ShotToShotCharacterization()
    XTCAVRetrieval.SetDataSource(ds)

    xtcavType   = psana.Camera.FrameV1
    xtcavCamera = psana.Source('DetInfo(XrayTransportDiagnostic.0:Opal1000.0)')

    if rank == 0 : print '\nOutputing to :', args.h5dir + args.h5fnam

    processed_events_me = 0
    processed_events    = 0
    dropped_events      = 0
    
    powers = None
    ts     = None
    delays = None
    energyperpulses = None
    timestamps = None
    
    for i, evt in enumerate(ds.events()):
        if not XTCAVRetrieval.SetCurrentEvent(evt):         
            continue
         
        processed_events += 1
        
        if processed_events % size != rank: continue     # different ranks look at different events

        try :
            timestamp           = evt.get(psana.EventId).__str__()
            t, power      , ok1 = XTCAVRetrieval.XRayPower()  
            delay         , ok2 = XTCAVRetrieval.InterBunchPulseDelayBasedOnCurrent()        
            energyperpulse, ok3 = XTCAVRetrieval.XRayEnergyPerBunch()
                    
            ok = ok1 and ok2 and ok3

            if not ok :
                dropped_events += 1

        except Exception as e:
            print e
            power           = None
            ok              = False
            dropped_events += 1
       
        if powers is None and power is not None :
            powers = np.zeros( (args.chunksize, ) + power.shape, dtype=np.float32)
            ts     = np.zeros( (args.chunksize, ) + t.shape, dtype=np.float32)
            delays = np.zeros( (args.chunksize, ) + delay.shape,  dtype=np.float32)
            energyperpulses = np.zeros( (args.chunksize, ) + energyperpulse.shape,  dtype=np.float32)
            event_numbers   = np.zeros( (args.chunksize, ),  dtype=np.int64)
            #
            timestamp  = np.array(timestamp)
            timestamps = np.zeros( (args.chunksize, ) + timestamp.shape,  dtype=timestamp.dtype)

        j = processed_events_me % args.chunksize

        event_numbers[j] = i
        if ok :
            powers[j]          = power
            ts[j]              = t
            delays[j]          = delay
            energyperpulses[j] = energyperpulse
            timestamps[j]      = timestamp

        if rank == 0 :
            print 'no. of evnts, processed, dropped: {0:5d} {1:3} {2:3} {3} \r'.format(i, processed_events_me, dropped_events, evt.get(psana.EventId)),
            sys.stdout.flush() 

        processed_events_me += 1

        # collect to rank 0:
        if processed_events_me % args.chunksize == 0 :
            fnam = args.h5dir + args.h5fnam
            collect_and_write(fnam, processed_events, args.chunksize, \
                    [['event_numbers', event_numbers], \
                     ['xray_power', powers], \
                     ['timestamp' , timestamps], \
                     ['time_fs', ts], \
                     ['delay', delays], \
                     ['energy_per_pulse', energyperpulses], \
                     ['event_number', powers]]) 
 
        """
        if processed_events_me % args.chunksize == 0 :
            event_numbers_tot = collect(event_numbers)

            if rank == 0 :
                j = np.argsort(event_numbers_tot)
            
            powers_tot          = collect(powers)
            timestamps_tot      = collect(timestamps)
            ts_tot              = collect(ts)
            delays_tot          = collect(delays)
            energyperpulses_tot = collect(energyperpulses)
            
            # write to file
            if rank == 0 :
                fnam = args.h5dir + args.h5fnam
                write_h5(fnam, 'timestamps',        processed_events, timestamps_tot[j])
                write_h5(fnam, 'xray_power',        processed_events, powers_tot[j])
                write_h5(fnam, 'time_fs',           processed_events, ts_tot[j])
                write_h5(fnam, 'delays',            processed_events, delays_tot[j])
                write_h5(fnam, 'energy_per_pulse',  processed_events, energyperpulses_tot[j])
                write_h5(fnam, 'event_numbers',     processed_events, event_numbers_tot[j])
        """

        #if processed_events_me == 1000 :
        #    break
