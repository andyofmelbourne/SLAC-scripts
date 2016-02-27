#!/usr/bin/env python

"""
Get xtcav data and periodically display it

show: 
    -- the raw electron map
    -- the power vs time plot
    -- 2D image stack of the power plots
"""

import pyqtgraph as pg
from PyQt4 import QtGui, QtCore
import signal
import collections
import numpy as np

from mpi4py import MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

from xtcav_powerstack import *

def send_to_gui(processed_events, output):
    """
    grab the output of the xtcav analysis then send it to 
    """
    #print rank, 'sending to gui:'
    comm.send([processed_events, output], dest=0, tag=rank)


class Application():
    
    def __init__(self):
        # start a pyqtgraph application (sigh...)
        self.buffer_depth = 100
        
        # Always start by initializing Qt (only once per application)
        app = QtGui.QApplication([])

        # powerstack
        self.powerstack_init = True
        self.xray_power   = collections.deque(maxlen = self.buffer_depth)
        
        self.plt_powerstack = pg.PlotItem(title = 'xray power vs event')
        self.w_powerstack = pg.ImageView(view = self.plt_powerstack)
            
        bottom = self.plt_powerstack.getAxis('bottom')
        bottom.setLabel('delay (fs)')

        left = self.plt_powerstack.getAxis('left')
        left.setLabel('event number ')

        # power vs delay
        self.w_xray_power = pg.plot(title = 'xray power vs delay')
        self.w_xray_power.setLabel('bottom', 'delay (fs)')
        self.w_xray_power.setLabel('left', 'power (GW)')

        # delay
        self.delay        = collections.deque(maxlen = self.buffer_depth)
        self.event_number = collections.deque(maxlen = self.buffer_depth)
        self.w_delay = pg.plot(title = 'time between the two xray pulses')
        self.w_delay.setLabel('bottom', 'event')
        self.w_delay.setLabel('left', 'delay (fs)')

        # xtcav images
        self.plt_xtcav  = pg.PlotItem(title = 'processed xtcav image')
        self.xtcav_init = True
        self.w_xtcav = pg.ImageView(view = self.plt_xtcav)

        bottom = self.plt_xtcav.getAxis('bottom')
        bottom.setLabel('delay (fs)')

        left = self.plt_xtcav.getAxis('left')
        left.setLabel('power (MeV)')

        ## Start the Qt event loop
        signal.signal(signal.SIGINT, signal.SIG_DFL)    # allow Control-C
        
        self.catch_data()

        sys.exit(app.exec_())

    def catch_data(self):
        for r in range(1, size):
            if comm.Iprobe(source = r, tag = r):
                #print 'gui: I recieved data from rank', r
                processed_events, output = comm.recv(source=r, tag=r)
                
                self.update_display(output)
                
                QtGui.QApplication.processEvents()

        QtCore.QTimer.singleShot(0, self.catch_data)

    def update_display(self, output):
        # power vs delay
        self.w_xray_power.clear()
        self.w_xray_power.plot(output['time'][-1][0], output['power'][-1][0])
        self.w_xray_power.plot(output['time'][-1][0], output['power_ecom'][-1][0], pen=pg.mkPen('r'))
        self.w_xray_power.plot(output['time'][-1][0], output['power_erms'][-1][0], pen=pg.mkPen('g'))

        # power stack
        self.xray_power.append(output['power'][-1][0])
        
        #scale = (ts[-1][0][-1] / len(self.xray_power[-1]), 1.)
        scale = (output['time'][-1][0][-1] - output['time'][-1][0][-2], 1.)
        if self.powerstack_init :
            self.w_powerstack.setImage(np.array(self.xray_power).T, autoRange = True, scale = scale)
            self.w_powerstack.show()
            self.powerstack_init = False
        else :
            self.w_powerstack.setImage(np.array(self.xray_power).T, autoRange = False, autoLevels = False, autoHistogramRange = False, scale = scale)
        
        self.w_powerstack.getView().invertY(False)
        #box = self.w_powerstack.getImageItem().getViewBox()
        #box.setAspectLocked(True, ratio = ts[-1][0][-1], powers[-1][0][-1])

        # delay
        #print 'event number :', event_numbers[-1]
        self.delay.append(np.abs(output['delay'][-1][0] - output['delay'][-1][1]))
        self.event_number.append(output['event_number'][-1])
        self.w_delay.clear()
        self.w_delay.plot(np.array(self.event_number), np.array(self.delay))
        
        # xtcav images
        scale = (-output['image_fs_scale'], output['image_MeV_scale'])
        if self.xtcav_init :
            self.w_xtcav.setImage(output['xtcav_image'][-1][0].T, scale = scale)
            self.xtcav_init = False
            self.w_xtcav.show()
        else :
            self.w_xtcav.setImage(output['xtcav_image'][-1][0].T, autoRange = False, autoLevels = False, autoHistogramRange = False, scale = scale)
        self.w_xtcav.getView().invertY(False)

if __name__ == "__main__":
    args = parse_cmdline_args()
    
    if rank == 0 :
        app = Application()
    
    process_xtcav_loop(args, send_to_gui)
