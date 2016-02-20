#!/usr/bin/env python
"""
Designed to be run with 4 cores
everyone computes their own histograms 
for each quadrant then we collect them
at the end. I do not know if 2 cores 
trying to access the same event is slow...
"""

import sys
import os
import argparse
import ConfigParser
import numpy as np

def parse_cmdline_args():
    parser = argparse.ArgumentParser(prog = 'mpirun -np 4 [OPTIONS] makehist.py', description='calculate the adu histogram of a run')
    parser.add_argument('-c', '--config', type=str, \
                        help="file name of the configuration file")
    parser.add_argument('-s', '--source', type=str, \
                help="psana source string (e.g exp=cxi01516:run=10:idx)")
    args = parser.parse_args()

    # check that args.ini exists
    if args.config is None :
        args.config = 'config.ini'
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

def psana_obj_from_string(name):
    """Converts a string into a psana object type.
    
    Takes a string and returns the python object type described by the string.

    Args:
        name (str): a string describing a python type.
    
    Returns:
        mod (type): the python type described by the string.
    """
    
    components = name.split('.')
    mod = __import__(components[0])
    for comp in components[1:]:
        mod = getattr(mod, comp)
    return mod

if __name__ == "__main__":
    #-----------------------------
    # Input parsing and allocation
    #-----------------------------
    args = parse_cmdline_args()
    
    config = ConfigParser.ConfigParser()
    config.read(args.config)
    params = parse_parameters(config)

    if args.source is None :
        config = ConfigParser.ConfigParser()
        config.read(args.config)
        params = parse_parameters(config)
        source = 'exp='+params['source']['exp']+':'+'run='+str(params['source']['run'])+':idx'
        exp = params['source']['exp']
        run = params['source']['run']
    else :
        source = args.source
        exp = source.split('=')[1].split(':')[0]
        run = source.split('=')[2].split(':')[0]
    
    import psana
    import h5py
    ds = psana.DataSource(source)

    detector_psana_source = psana.Source(params['source']['detector_psana_source'])
    detector_psana_type   = psana_obj_from_string(params['source']['detector_psana_type'])

    def evt_to_array(evt, rank):
        im    = evt.get(detector_psana_type, detector_psana_source)
        try :
            im_np = im.quads(rank).data()
        except :
            im_np = im.frame(rank).data()
        return im_np

    # output
    import string
    if params['output']['match'] :
        h5name = params['output']['fnam']
        h5name = string.replace(h5name, 'exp', exp)
        h5name = string.replace(h5name, 'run', 'r' + str(run).zfill(4))
    else :
        h5name = params['output']['fnam']

    h5path = params['output']['h5path']
    h5dir  = params['output']['h5dir']

    from mpi4py import MPI
    comm = MPI.COMM_WORLD
    rank = comm.Get_rank()
    size = comm.Get_size()

    if rank == 0 : print '\nOutputing to :', h5dir + h5name + ':' + h5path

    hist_dtype   = np.dtype(params['histogram']['hist_dtype'])
    buffer_dtype = np.dtype(params['histogram']['buffer_dtype'])
    cspad_shape  = tuple(params['histogram']['shape'])
    bins         = np.arange(params['histogram']['bins'][0], params['histogram']['bins'][1] + 1, 1).astype(np.int)
    buffersize   = params['histogram']['buffer_size']
    buffer  = np.empty( (buffersize,) + cspad_shape[1:], dtype=buffer_dtype)
    hist    = np.zeros( cspad_shape[1:] + bins[:-1].shape,    dtype=buffer_dtype)

    # darkcal
    if rank == 0:
        darkSumFnam = params['histogram']['darkcal']
        
        f = h5py.File(darkSumFnam, 'r')
        darkcal = f['data/data'].value.astype(np.float64) / float(f['number of frames'].value)
        f.close()
        darkcals = [darkcal[i] for i in range(darkcal.shape[0])]
        darkcal  = darkcals
    else :
        darkcal = None

    comm.barrier()
    if rank == 0 : print '\n scattering the darkcal to everyone...'
    darkcal = comm.scatter(darkcal, root=0)
    #print rank, darkcal.shape, buffer.shape, cspad_shape

    #-----------------------------
    # Actual meat
    #-----------------------------
    dropped_events = 0
    j = 0
    for run in ds.runs():
        times    = run.times()
        if rank == 0 :
            print 'Number of frames to process:', len(times)
        
        for i in range(len(times)):
            try :
                evt = run.event(times[i])
                
                # add to buffer
                #temp = evt_to_array(evt, rank)
                #print rank, buffer.shape, temp.shape
                #buffer[j] = temp
                buffer[j] = evt_to_array(evt, rank)
                j += 1

                if j == buffersize  :
                    j = 0

                    # darkcal
                    buffer -= darkcal
                    
                    # common mode
                    medians  = np.median(buffer, axis=-1)
                    buffer  -= medians[..., np.newaxis]

                    # add the histogram of the buffer to the histogram
                    # ------------------------------------------------
                    # loop over each pixel
                    buffer_T = buffer.T.reshape((-1, buffer.shape[0]), order='F')
                    
                    for ii in range(buffer_T.shape[0]):
                        #h, b          = np.histogram(buffer[:, ii, jj], bins=bins)
                        a             = np.rint(buffer_T[ii]).astype(np.int)
                        a             = a[np.where(a < bins[-1])]
                        a            -= bins[0]
                        a             = a[np.where(a >= 0)]
                        h             = np.bincount( a, minlength=bins.shape[0]-1)
                        hist[np.unravel_index(ii, (hist.shape[:-1]))] += h
            except Exception as e :
                print e
                dropped_events += 1

            if rank == 0:
                print 'no. of evnts, rank, dropped: {0:5d} {1:3} {2:3} {3} \r'.format(i, rank, dropped_events, evt.get(psana.EventId)),
                sys.stdout.flush()
    del buffer
    del medians

    #--------------------------------------------------
    # Get everyones's hists and put them into a h5 file
    #--------------------------------------------------
    comm.barrier()
    if rank == 0:
        print ''
        print ''
        print '\n outputing histograms to:', h5dir, h5name, h5path
        f    = h5py.File(h5dir + h5name, 'w')
        dset = f.create_dataset(h5path, (cspad_shape + bins[:-1].shape), compression='gzip')

        # output 0's hist
        print '\n outputing rank', 0
        dset[0, ...] = hist.copy()
        del hist

        # and everyone elses
        for i in range(1, size):
            print '\n outputing rank', i
            hist = comm.recv(source = i, tag = i)
            dset[i, ...] = hist.copy()
            del hist
        
        f.close()
        print '\n done!!'

    else :
        comm.send(hist, dest=0, tag=rank)
