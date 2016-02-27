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
        args.skip       = params['params']['process_every']
        args.fit_gaus_delay = params['params']['fit_gaus_delay']
        args.delay_bound = params['params']['delay_bound']
    
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

def gaus(x, *p):
    return p[0] * np.exp(-(x-p[1])**2 / (2. * p[2]**2))

def gaus_fit(y, x = None , return_fit = False):
    import scipy.optimize
    if x is None :
        x = np.indices(y.shape)[0].astype(np.float64)
    
    p0 = [y.max(), 0.0, x.shape[0]/4.]
    popt, pcov = scipy.optimize.curve_fit(gaus, x, y.astype(np.float64), p0 = p0)
    
    if return_fit :
        return popt, gaus(x, *popt)
    else :
        return popt

def gaus2(x, *p):
    p0 = p[:3] 
    p1 = p[3:] 
    return gaus(x, *p0) + gaus(x, *p1) 

def gaus2_fit(y, x = None , return_fit = False):
    import scipy.optimize
    if x is None :
        x = np.indices(y.shape)[0].astype(np.float64)
    
    p0 = np.random.random((6))
    residual = lambda i : gaus2(x, *i) - y
    popt, flag = scipy.optimize.leastsq(residual, p0)
    
    if return_fit :
        return popt[:3], popt[3:], gaus2(x, *popt), flag
    else :
        return popt[:3], popt[3:], flag


def write_h5(fnam, path, index, data):
    import h5py
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
    stuff_tot  = {}
    stuff_tot['event_number'] = collect(stuff['event_number'])
    
    if rank == 0 :
        j = np.argsort(stuff_tot['event_number'])
    
    for k in stuff.keys():
        if k != 'event_number':
            stuff_tot[k] = collect(stuff[k])

    # write to file
    if rank == 0 :
        for k in stuff_tot.keys():
            write_h5(fnam, k, processed_events, stuff_tot[k][j])

def process_xtcav_loop(args, callback):
    """
    loops over xtcav events then calls 'callback' after every 
    rank has processed args.chunksize.

    callback
    """
    import psana
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
    skipped             = 0
    
    output = {}
    output['power']          = None
    output['power_ecom']     = None
    output['power_erms']     = None
    output['time']           = None
    output['delay']          = None
    output['energyperpulse'] = None
    output['timestamp']      = None
    output['xtcav_image']    = None
    output['event_number']   = None
    output['image_fs_scale'] = None
    output['image_MeV_scale']= None
    output['reconstruction_agreement'] = None

    for i, evt in enumerate(ds.events()):
        if not XTCAVRetrieval.SetCurrentEvent(evt):         
            continue
         
        processed_events += 1
        
        if processed_events % size != rank: continue     # different ranks look at different events

        if skipped != args.skip :
            skipped += 1
            continue
        else :
            skipped = 0
            
        try :
            timestamp           = evt.get(psana.EventId).__str__()
            t, power      , ok1 = XTCAVRetrieval.XRayPower()  
            t, power_ecom , ok2 = XTCAVRetrieval.XRayPowerCOMBased()  
            t, power_erms , ok3 = XTCAVRetrieval.XRayPowerRMSBased()  

            # delay calculation
            if args.fit_gaus_delay :
                p0, p1, ok4 = gaus2_fit(np.sum(power, axis=0), x = t[0], return_fit = False)
                dp = p1[1] - p0[1]

                if np.abs(dp) > args.delay_bound :
                    ok4 = False
                    delay = np.array([0.0, 0.0])
                elif dp > 0. :
                    delay       = np.array([p0[1], p1[1]]) 
                else :
                    delay       = np.array([p1[1], p0[1]]) 
                print np.abs(dp)
            else :
                delay, ok4  = XTCAVRetrieval.InterBunchPulseDelayBasedOnCurrent()        
            
            energyperpulse, ok5 = XTCAVRetrieval.XRayEnergyPerBunch()
            xtcav_image   , ok6 = XTCAVRetrieval.ProcessedXTCAVImage()
            reconstruction_agreement, ok7 = XTCAVRetrieval.ReconstructionAgreement()
            fs_scale            = XTCAVRetrieval._eventresultsstep2['PU']['xfsPerPix']
            mev_scale           = XTCAVRetrieval._eventresultsstep2['PU']['yMeVPerPix']
                    
            ok = ok1 and ok2 and ok3 and ok4

            if not ok :
                dropped_events += 1

        except Exception as e:
            print e
            power           = None
            ok              = False
            dropped_events += 1
       
        if output['power'] is None and power is not None :
            output['power']          = np.zeros( (args.chunksize, ) + power.shape, dtype=np.float32)
            output['power_ecom']     = np.zeros( (args.chunksize, ) + power.shape, dtype=np.float32)
            output['power_erms']     = np.zeros( (args.chunksize, ) + power.shape, dtype=np.float32)
            output['time']           = np.zeros( (args.chunksize, ) + t.shape, dtype=np.float32)
            output['delay']          = np.zeros( (args.chunksize, ) + delay.shape,  dtype=np.float32)
            output['energyperpulse'] = np.zeros( (args.chunksize, ) + energyperpulse.shape,  dtype=np.float32)
            output['xtcav_image']    = np.zeros( (args.chunksize, ) + xtcav_image.shape,  dtype=np.float32)
            output['event_number']   = np.zeros( (args.chunksize, ),  dtype=np.int64)
            output['image_fs_scale'] = np.zeros( (args.chunksize, ),  dtype=np.float)
            output['image_MeV_scale']= np.zeros( (args.chunksize, ),  dtype=np.float)
            output['reconstruction_agreement'] = np.zeros( (args.chunksize, ), dtype=np.float)
            #
            timestamp  = np.array(timestamp)
            output['timestamp'] = np.zeros( (args.chunksize, ) + timestamp.shape,  dtype=timestamp.dtype)

        j = processed_events_me % args.chunksize

        output['event_number'][j] = i
        if ok :
            output['power'][j]          = np.abs(power) # hack because of bad reference
            output['power_ecom'][j]     = np.abs(power_ecom) # hack because of bad reference
            output['power_erms'][j]     = np.abs(power_erms) # hack because of bad reference
            output['time'][j]           = t
            output['delay'][j]          = delay
            output['energyperpulse'][j] = energyperpulse
            output['timestamp'][j]      = timestamp
            output['image_fs_scale'][j] = fs_scale
            output['image_MeV_scale'][j]= mev_scale
            output['reconstruction_agreement'][j]= reconstruction_agreement
            
            # pretty anoying, the xtcav images change shape
            shape   = list(output['xtcav_image'].shape)
            shape_p = xtcav_image.shape
            if shape_p[1] > shape[2]:
                shape[2] = shape_p[1]

            if shape_p[2] > shape[3]:
                shape[3] = shape_p[2]
            
            output['xtcav_image'].resize(shape) 
            
            output['xtcav_image'][j][:, :shape_p[1], :shape_p[2]] = xtcav_image

        if rank == 0 :
            print 'no. of evnts, processed, dropped: {0:5d} {1:3} {2:3} {3} \r'.format(i, processed_events_me, dropped_events, tiemstamp),
            sys.stdout.flush() 

        processed_events_me += 1

        # collect to rank 0:
        if processed_events_me % args.chunksize == 0 :
            callback(processed_events, output)

if __name__ == "__main__":
    args = parse_cmdline_args()
    
    def callback(processed_events, output):
        fnam = args.h5dir + args.h5fnam
        collect_and_write(fnam, processed_events, args.chunksize, output)

    process_xtcav_loop(args, callback)

