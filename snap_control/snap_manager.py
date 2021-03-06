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

try:
    import hickle as hkl
    HAS_HKL = True
except:
    HAS_HKL = False

from multiprocessing import JoinableQueue

from threading import Thread


class SnapManager(object):
    def __init__(self, board_list):
        self.snap_boards = [SnapBoard(bl) for bl in board_list]
        for s in self.snap_boards:
             s.logger     = logging.getLogger(s.host)
             if s.adc is None:
                 s.adc = SnapAdc(self)
             s.adc.logger = logging.getLogger(s.host + '-adc')

        self.task_queue = JoinableQueue()

    def _run(self, q, proc_id, fn_to_run, *args, **kwargs):
        return_val = fn_to_run(*args, **kwargs)
        q.put([proc_id, return_val])
        q.task_done()

    def _run_on_all(self, fn_to_run, *args, **kwargs):
        q = JoinableQueue()
        for s in self.snap_boards:
            s_name = s.host
            try:
                method = getattr(s, fn_to_run)
            except AttributeError:
                try:
                    method = getattr(s.adc, fn_to_run)
                except AttributeError:
                    raise RuntimeError("Cannot find method %s" % fn_to_run)

            # Setup arguments and keyword args
            all_args = [q, s_name, method]
            if kwargs is None:
                kwargs = {}
            if args is not None:
                for aa in args:
                    all_args.append(aa)
            t = Thread(target=self._run,
                       name=s_name,
                       args=all_args,
                       kwargs=kwargs)
            t.daemon = True
            t.start()
        q.join()

        # Iterate through queue and
        outdict = {}
        for ii in range(0, len(self.snap_boards)):
            d_key, d_out = q.get()
            outdict[d_key] = d_out
        return outdict

    def program(self, boffile, gain=1, demux_mode=1):
        self._run_on_all('program', boffile, gain, demux_mode)

    def recalibrate(self):
        self._run_on_all('calibrate')

    def set_debug(self):
        self._run_on_all('set_debug')

    def set_inputs(self, input_id):
        self._run_on_all('set_inputs', input_id)

    def is_adc16_based(self):
        self._run_on_all('is_adc16_based')

    def fpga_set_demux(self, fpga_demux):
        self._run_on_all('fpga_set_demux', fpga_demux)

    def write_int(self, device_name, integer, blindwrite=False, word_offset=0):
        self._run_on_all('write_int', device_name, integer, blindwrite=False, word_offset=0)

    def write(self, device_name, data, offset=0):
        self._run_on_all('write', device_name, data, offset=0)

    def read_int(self, device_name, word_offset=0):
        return self._run_on_all('read_int', device_name, word_offset)

    def read_uint(self, device_name, word_offset=0):
        return self._run_on_all('read_uint', device_name, word_offset)

    def get_system_information(self, filename=None, fpg_info=None):
        return self._run_on_all('get_system_information', filename, fpg_info)

    def listbof(self, run_on_all=True):
        if run_on_all:
            return self._run_on_all('listbof')
        else:
            s = self.snap_boards[0]
            return s.listbof()

    def listdev(self, run_on_all=True):
        if run_on_all:
            return self._run_on_all('listdev')
        else:
            s = self.snap_boards[0]
            return s.listbof()

    def estimate_fpga_clock(self, run_on_all=True):
        if run_on_all:
            return self._run_on_all('estimate_fpga_clock')
        else:
            s = self.snap_boards[0]
            return s.estimate_fpga_clock()

    def check_rms(self):
        d = {}
        dd = self._run_on_all('check_rms')

        for subd in dd.values():
            d.update(subd)

        for key in sorted(d.keys()):
            print("%s: %2.2f" % (key, d[key]))

    def grab_adc_snapshot(self):
        d = {}
        dd = self._run_on_all('grab_adc_snapshot')

        for subd in dd.values():
            d.update(subd)
        return d

    def check_calibration(self):
        dd = self._run_on_all('check_calibration')
        for k in sorted(dd.keys()):
            print dd[k]

    def save_adc_snapshot(self, filename=None):
        d = self.grab_adc_snapshot()

        if HAS_HKL:
            print("Saving data...")

            if filename is None:
                now = datetime.now()
                now_str = now.strftime("%Y-%m-%d-%H%M%S")
                filename = 'adc_snapshot_%s.hkl' % now_str
            hkl.dump(d, filename)
            print("OK")
        else:
            print("Python hickle module not installed, cannot export data.")


