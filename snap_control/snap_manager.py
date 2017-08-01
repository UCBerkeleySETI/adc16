#!/usr/bin/env python
"""
# snap_manager.py

Controller to issue commands to the snap boards
"""


from .snap_adc import SnapAdc
from .snap_board import SnapBoard
from .snap_plot import demux_data

import logging
import numpy as np
from datetime import datetime
import hickle as hkl


from threading import Thread


class SnapManager(object):
    def __init__(self, board_list):
        self.snap_boards = [SnapBoard(bl) for bl in board_list]
        for s in self.snap_boards:
             s.logger     = logging.getLogger(s.host)
             if s.adc is None:
                 s.adc = SnapAdc(self)
             s.adc.logger = logging.getLogger(s.host + '-adc')

    def _run(self, method_name, *args, **kwargs):
        """ Run a method on all snap boards """
        thread_list = []
        for s in self.snap_boards:

            # Retrieve the class method to run by name
            method = getattr(s, method_name)

            # Check if we have keywords and arguments and create thread accordingly
            if args is not None and kwargs is None:
                t = Thread(target=method, name=s.host, args=args)
            elif args is None and kwargs is not None:
                t = Thread(target=method, name=s.host, kwargs=kwargs)
            elif args is not None and kwargs is not None:
                t = Thread(target=method, name=s.host, args=args, kwargs=kwargs)
            else:
                t = Thread(target=method, name=s.host)

            # Start thread
            t.daemon = True
            t.start()
            thread_list.append(t)

        # Wait for all threads to finish
        for t in thread_list:
            t.join()


    def program(self, boffile, gain=1, demux_mode=1):
        self._run('program', boffile, gain, demux_mode)

    def check_calibration(self):
        for s in self.snap_boards:
            for chip_id in (0,1,2):
                s.adc.enable_pattern('deskew')
                snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_id))
                s.adc.clear_pattern()
                d1 = demux_data(snapshot, 4)
                print("%06s ADC %i: %s" % (s.host, chip_id, np.allclose(d1, 42)))

    def set_debug(self):
        self._run('set_debug')

    def set_inputs(self, input_id):
        self._run('set_inputs', input_id)



    def check_rms(self):
        for s in self.snap_boards:
            for chip_id in (0,1,2):
                snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_id))
                rms = np.std(snapshot)
                print("%06s ADC %i: %2.2f" % (s.host, chip_id, rms))
         
    def grab_adc_snapshot(self, filename=None):
        d = {}
        for s in self.snap_boards:
            for chip_id in (0, 1, 2):
                snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_id))
                #d1 = np.array(demux_data(snapshot, 4), dtype='int32')
                d["%s-%i" % (s.host, chip_id)] = snapshot
        return d
                
    def save_adc_snapshot(self, filename=None):
        d = self.grab_adc_snapshot()

        print("Saving data...")

        if filename is None:
            now = datetime.now()
            now_str = now.strftime("%Y-%m-%d-%H%M%S")
            filename = 'adc_snapshot_%s.hkl' % now_str
        hkl.dump(d, filename)
        print("OK")

