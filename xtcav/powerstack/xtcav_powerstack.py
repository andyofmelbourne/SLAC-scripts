#!/usr/bin/env python

import sys
import os
import argparse
import ConfigParser
import numpy as np
import time
import datetime
import copy

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

rank_debug = 1

def parse_cmdline_args():
    parser = argparse.ArgumentParser(description='Get the xray power vs time profile for every shot')
    parser.add_argument('-c', '--config', type=str, \
                        help="file name of the configuration file")
    """
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
    """
    args = parser.parse_args()

    # check that args.ini exists
    if not os.path.exists(args.config):
        raise NameError('config file does not exist: ' + args.config)

    if args.config is not None :
        config = ConfigParser.ConfigParser()
        config.read(args.config)
        params = parse_parameters(config)
        
        # source
        args.experiment     = str(params['source']['exp'])
        args.run            = str(params['source']['run'])
        args.mode           = params['source']['mode']

        # params
        args.calib          = params['params']['calib']
        args.maxshots       = params['params']['maxshots']
        if args.maxshots is None :
            args.maxshots = np.inf
        args.bunches        = params['params']['bunches']
        args.chunksize      = params['params']['chunksize']
        args.process_every  = params['params']['process_every']
        args.delay_bound    = params['params']['delay_bound']
        if args.delay_bound is None or args.delay_bound is 'inf':
            args.delay_bound = np.inf

        # output
        args.h5fnam          = params['output']['h5fnam']
        args.matchfnam       = params['output']['matchfnam']
        args.h5dir           = params['output']['h5dir']

        # output_items
        if rank == rank_debug : print '\nLoading output items from the config file:'
        if rank == rank_debug :
            for k in params['output_items'].keys():
                print '\t', k, params['output_items'][k]
        args.power           = params['output_items']['power']
        args.power_ecom      = params['output_items']['power_ecom']
        args.power_erms      = params['output_items']['power_erms']
        args.power_ebeam     = params['output_items']['power_ebeam']
        args.time            = params['output_items']['time']
        args.delay           = params['output_items']['delay']
        args.delay_gaus      = params['output_items']['delay_gaus']
        args.energyperpulse  = params['output_items']['energyperpulse']
        args.timestamp       = params['output_items']['timestamp']
        args.xtcav_image     = params['output_items']['xtcav_image']
        args.event_number    = params['output_items']['event_number']
        args.image_fs_scale  = params['output_items']['image_fs_scale']
        args.image_mev_scale = params['output_items']['image_mev_scale']
        args.reconstruction_agreement = params['output_items']['reconstruction_agreement']
    
    import string
    if args.matchfnam :
        args.h5fnam = string.replace(args.h5fnam, 'exp', args.experiment)
        args.h5fnam = string.replace(args.h5fnam, 'run', 'r' + str(args.run).zfill(4))

    if args.mode != '' and args.mode[0] != ':' :
        args.mode = ':' + args.mode

    args.source = 'exp='+args.experiment+':'+'run='+str(args.run)+args.mode

    return args, params


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
    
    #p0 = np.random.random((6))
    p0 = np.array([20., -40., 3., 20, +40., 3.])
    residual = lambda i : gaus2(x, *i) - y
    popt, flag = scipy.optimize.leastsq(residual, p0)
    
    if return_fit :
        return popt[:3], popt[3:], gaus2(x, *popt), flag
    else :
        return popt[:3], popt[3:], flag


def write_h5(fnam, path, processed, data):
    import h5py
    f = h5py.File(fnam, 'a')
    try :
        dset = f[path]
        dset.resize(processed, axis = 0)
    except Exception as e :
        dset = f.create_dataset(path, data.shape, maxshape = (None,) + data[0].shape, dtype=data.dtype)

    print '\n'
    print 'processed - data.shape[0]: processed', processed - data.shape[0], processed

    print path, dset.shape, data.shape
    dset[processed - data.shape[0]: processed] = data 
    f.close()


def collect(data):
    if rank == 0 :
        data_rec = [data.copy()]
        for i in range(1, size):
            print 'gathering data from rank:', i
            data_rec.append( comm.recv(source = i, tag = i) )
        data = np.array([e for es in data_rec for e in es])
    else :
        comm.send(data, dest=0, tag=rank)
    return data


def collect_and_write(fnam, processed_events, chunksize, stuff):
    stuff_tot  = {}
    print 'rank: ', rank, 'collecting: event_number'
    stuff_tot['event_number'] = collect(stuff['event_number'])
    
    if rank == 0 :
        j = np.argsort(stuff_tot['event_number'])
    
    for k in stuff.keys():
        if k != 'event_number' and stuff[k] is not False :
            print 'rank: ', rank, 'collecting: ', k
            stuff_tot[k] = collect(stuff[k])

    # write to file
    if rank == 0 :
        for k in stuff_tot.keys():
            print 'writing', k, processed_events, stuff_tot[k][j].shape
            write_h5(fnam, k, processed_events, stuff_tot[k][j])

def process_xtcav_loop(args, params, callback):
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

    if rank == rank_debug : print 'sourcing:', args.source
    ds = psana.DataSource(args.source)

    #XTCAV Retrieval (setting the data source is useful to get information such as experiment name)
    XTCAVRetrieval = xtcav.ShotToShotCharacterization.ShotToShotCharacterization()
    XTCAVRetrieval.SetDataSource(ds)

    xtcavType   = psana.Camera.FrameV1
    xtcavCamera = psana.Source('DetInfo(XrayTransportDiagnostic.0:Opal1000.0)')

    if rank == rank_debug : print '\nOutputing to :', args.h5dir + args.h5fnam

    processed_events_me = 0
    processed_events    = 0
    dropped_events      = 0
    skipped             = 0
    
    if rank == rank_debug : print '\noutputing:'
    output = {}
    output['ok'] = None
    for k in params['output_items'].keys() :
        if params['output_items'][k] :
            output[k] = None
            if rank == rank_debug : print '\t', k
        else :
            output[k] = False
    
    event  = copy.copy(output)
    init = True

    for i, evt in enumerate(ds.events()):
        """
        Process the event: 
            - A 'processed_event' is an event that has xtcav data in it
            - A 'dropped_event' is an event that this rank attempted to analyse but could not
            - A 'processed_event_me' is an event that this rank processed successfully
            - A 'skipped' event is an event that has xtcav data but that we intentionally skip to speed up analysis
        """
        if not XTCAVRetrieval.SetCurrentEvent(evt):         
            continue
         
        processed_events += 1
        
        # different ranks look at different events
        if processed_events % size != rank: continue     

        # skip to speed things up
        if skipped != args.process_every:
            skipped += 1
            continue
        else :
            skipped = 0
            
        #===============
        # event analysis
        #===============
        try :
            ok = []
            event['event_number'] = i
            if output['timestamp'] is not False :
                event['timestamp'] = evt.get(psana.EventId).__str__()
            if output['power'] is not False :
                event['time'], event['power'], okt = XTCAVRetrieval.XRayPower()  
                ok.append(okt)
            if output['power_ecom'] is not False :
                event['time'], event['power_ecom'], okt = XTCAVRetrieval.XRayPowerCOMBased()  
                ok.append(okt)
            if output['power_erms'] is not False :
                event['time'], event['power_erms'] , okt = XTCAVRetrieval.XRayPowerRMSBased()  
                ok.append(okt)
            if output['power_ebeam'] is not False :
                xtcav, okt = XTCAVRetrieval.ProcessedXTCAVImage()
                event['power_ebeam'] = np.sum(xtcav, axis=(0, 1))
                ok.append(okt)
            if output['delay'] is not False :
                event['delay'], okt = XTCAVRetrieval.InterBunchPulseDelayBasedOnCurrent()        
                ok.append(okt)
            if output['energyperpulse'] is not False :
                event['energyperpulse'], okt = XTCAVRetrieval.XRayEnergyPerBunch()
                ok.append(okt)
            if output['xtcav_image'] is not False :
                event['xtcav_image'], okt = XTCAVRetrieval.ProcessedXTCAVImage()
                ok.append(okt)

            if output['image_fs_scale'] is not False :
                event['image_fs_scale'] = XTCAVRetrieval._eventresultsstep2['PU']['xfsPerPix']
            if output['image_mev_scale'] is not False :
                event['image_mev_scale'] = XTCAVRetrieval._eventresultsstep2['PU']['yMeVPerPix']
            if output['reconstruction_agreement'] is not False :
                event['reconstruction_agreement'], okt = XTCAVRetrieval.ReconstructionAgreement()
                ok.append(okt)

            # delay calculation
            if output['delay_gaus'] is not False :
                p0, p1, okt = gaus2_fit(np.abs(np.sum(event['power'], axis=0)), x = event['time'][0], return_fit = False)
                dp = p1[1] - p0[1]
                
                if np.abs(dp) > args.delay_bound or okt is False :
                    delay_gaus = np.array([0.0, 0.0])
                elif dp > 0. :
                    event['delay_gaus'] = np.array([p0[1], p1[1]]) 
                else :
                    event['delay_gaus'] = np.array([p1[1], p0[1]]) 

                if event['delay_gaus'] is None :
                    okt = False
                ok.append(okt)

            okt = True 
            for o in ok :
                okt = okt and o
            ok = okt
            event['ok'] = ok
            
            if not ok :
                dropped_events += 1
            else :
                processed_events_me += 1

            if not ok :
                dropped_events += 1
        except Exception as e:
            print e
            ok              = False
            dropped_events += 1
       
        #=========================
        # initialise output arrays
        #=========================
        if init and ok :
            if rank == rank_debug : print '\ninitialising arrays:'
            for k in event.keys() :
                if output[k] is not False :
                    if type(event[k]) == np.ndarray :
                        shape = list((args.chunksize, ) + event[k].shape)
                        if k == 'xtcav_image' :
                            shape[-1] = 512
                            shape[-2] = 512
                        elif k == 'power_ebeam' :
                            shape[-1] = 512
                        output[k] = np.zeros( shape, dtype=event[k].dtype)

                    if type(event[k]) in [float, np.float64, np.float32] :
                        output[k] = np.zeros( (args.chunksize, ), dtype=np.float)
                    
                    if type(event[k]) == int :
                        output[k] = np.zeros( (args.chunksize, ), dtype=np.int)

                    if type(event[k]) == bool :
                        output[k] = np.zeros( (args.chunksize, ), dtype=np.bool)
                    
                    if output[k] is not None :
                        if rank == rank_debug : print '\t', k, 
                        if rank == rank_debug : print output[k].dtype, output[k].shape

            
            event['timestamp']  = np.array(event['timestamp'])
            output['timestamp'] = np.zeros( (args.chunksize, ) + event['timestamp'].shape,  \
                                            dtype=event['timestamp'].dtype)
            if rank == rank_debug : print '\t', 'timestamp',
            if rank == rank_debug : print output['timestamp']
            if rank == rank_debug : print output['timestamp'].dtype, output['timestamp'].shape
            init = False

        #===================================
        # append event data to output arrays
        #===================================
        if ok :
            j = (processed_events_me - 1) % args.chunksize
            
            for k in event.keys():
                if k not in ['xtcav_image', 'power_ebeam'] :
                    if output[k] is not False :
                        output[k][j] = event[k]
                        if rank == rank_debug : print 'assigning:', k
                elif k == 'xtcav_image' and event['xtcav_image'] is not False :
                    # pretty anoying, the xtcav images change shape
                    shape   = list(output['xtcav_image'].shape)
                    shape_p = event['xtcav_image'].shape
                    if shape_p[1] > shape[2]:
                        shape[2] = shape_p[1]

                    if shape_p[2] > shape[3]:
                        shape[3] = shape_p[2]
                    
                    if output['xtcav_image'] is not False :
                        output['xtcav_image'].resize(shape) 
                        output['xtcav_image'][j][:, :shape_p[1], :shape_p[2]] = event['xtcav_image']
                        if rank == rank_debug : print 'assigning: xtcav_image'
                    
                    if 'power_ebeam' in event.keys() and output['power_ebeam'] is not False :
                        shape_e = list(output['power_ebeam'].shape)
                        shape_e[-1] = shape[-1]
                        output['power_ebeam'].resize(shape_e) 
                        output['power_ebeam'][j][:shape_p[2]] = event['power_ebeam'] 
                        if rank == rank_debug : print 'assigning: power_ebeam'
                #print '\n'
                #print k
                #print output[k][j]
        
        if rank == rank_debug :
            print 'no. of evnts, processed, dropped: {0:5d} {1:3} {2:3} {3} \r'.format(i, processed_events_me, dropped_events, event['timestamp'])

        # collect to rank 0:
        if processed_events_me % args.chunksize == 0 and processed_events_me > 0:
            print '\n', 'rank', rank, 'collecting. processed_events_me:', processed_events_me
            callback(size * processed_events_me, output)

        if size * processed_events_me > args.maxshots :
            print 'All done!!!'
            sys.exit()

if __name__ == "__main__":
    args, params = parse_cmdline_args()
    
    def callback(processed_events, output):
        fnam = args.h5dir + args.h5fnam
        collect_and_write(fnam, processed_events, args.chunksize, output)

    process_xtcav_loop(args, params, callback)

