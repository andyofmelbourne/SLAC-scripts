#!/usr/bin/env python

import sys
import os
import argparse
import ConfigParser
import numpy as np

def parse_cmdline_args():
    parser = argparse.ArgumentParser(prog = 'mpirun -np [NUM] [OPTIONS] darkcal.py', description='calculate the raw sum of all frames in a run')
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

    #im_sum = np.zeros((4, 512, 512), np.int64) # pnccd
    im_sum = None
    
    def evt_to_array(evt):
        im    = evt.get(detector_psana_type, detector_psana_source)
        try :
            # cspad
            im_np = np.array([im.quads(j).data() for j in range(im.quads_shape()[0])])
        except :
            try :
                # pnccds
                im_np = np.array([im.frame(j).data() for j in range(im.frame_shape()[0])])
            except :
                # opal
                im_np = im.data16()

        return im_np

    def native_to_slab(im_np, slab_shape = (1480, 1552), native_shape = (4, 8, 185, 388)):
        im_ij = np.zeros(slab_shape, dtype=im_np.dtype)
        for i in range(im_np.shape[0]):
            im_ij[:, i * native_shape[3]: (i+1) * native_shape[3]] = \
                    im_np[i].reshape((native_shape[1] * native_shape[2], native_shape[3]))
        return im_ij


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

    dropped_events = 0
    for run in ds.runs():
        times = run.times()[: params['params']['maxshots']]
        mylength = len(times) / size
        mytimes = times[rank*mylength:(rank+1)*mylength]
        if rank == 0 :
            print 'Number of frames to process:', len(times)
            print 'Each slave will process ', mylength, ' frames'
        
        for i in range(mylength):
            try :
                evt        = run.event(mytimes[i])
                im_np      = evt_to_array(evt)
                if im_sum is None :
                    im_sum = im_np.astype(np.int64)
                else :
                    im_sum += im_np
            except Exception as e:
                print e
                dropped_events += 1
            
            if rank == 0:
                print 'no. of evnts, rank, dropped: {0:5d} {1:3} {2:3} {3} \r'.format(i, rank, dropped_events, evt.get(psana.EventId)),
                sys.stdout.flush()

    im_sum_global = np.empty_like(im_sum)
    comm.Reduce(im_sum, im_sum_global)
    if rank == 0:
        print ''
        print ''
        print 'outputing the global sum...', h5dir, h5name, h5path

        f = h5py.File(h5dir + h5name, 'w')
        f.create_dataset(h5path, data = im_sum_global)
        f.create_dataset('number of frames', data = len(times))
        
        if params['output']['slab'] :
            im_slab = native_to_slab(im_sum_global)
            f.create_dataset('data/slab', data = im_slab)
         
        f.close()


