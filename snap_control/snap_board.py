"""
# snap_board.py

Python monitor and control of a CASPER SNAP board. Includes many
convenience functions for writing to the registers of the ADC chips,
calibrating the SERDES blocks, and accessing status info about the ADC16
design and clock status.  While most access will be done via the methods of
this class, there may be occasion to access the ADC16 controller directly
(via the #adc16_controller method, which returns a KATCP::Bram object)

"""

import logging
import time

import casperfpga

from .snap_adc import SnapAdc, GenericAdc

katcp_port = 7147


class SnapBoard(casperfpga.CasperFpga):
    """ Controller for a CASPER SNAP board.

    Provides monitor and control of a CASPER SNAP board
    """
    def __init__(self, hostname, katcp_port=7147, timeout=3,
                 uses_adc=True, verbose=False, **kwargs):
        super(SnapBoard, self).__init__(hostname, katcp_port, timeout)
        self.katcp_port = katcp_port

        if verbose == True:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # Wait up to timeout to see if ADC is connected
        t0 = time.time()
        while not self.is_connected():
            time.sleep(1e-3)
            if time.time() - t0 > timeout:
                break
                
        # Check if design has an ADC controller; if so, attach controller as self.adc
        self.adc = None
        self.uses_adc = uses_adc
        # If design has an ADC, attach Generic ADC to add logging and basic functionality
        if uses_adc:
            self.adc = GenericAdc(self)
            
        if self.is_connected():
            try:
                if self.is_adc16_based():
                    self.adc = SnapAdc(self)
            except RuntimeError:
                pass
        self.logger = logging.getLogger('SnapBoard')

    def __repr__(self):

        return "<SnapBoard host: %s port: %s>" % (self.host, self.katcp_port)
    
    def est_brd_clk(self):
        """Returns the approximate clock rate of the FPGA in MHz.

        Notes:
            Deprecated in favor of estimate_fpga_clock()
        """
        return self.estimate_fpga_clock()

    def program(self, boffile, gain=1, demux_mode=1, chips=('a', 'b', 'c')):
        """ Reprogram the FPGA with a given boffile AND calibrates

        Adds gain, demux_mode and chips params to katcp_wrapper's progdev

        Args:
            boffile (str): Name of boffile to program
            gain (int): ADC gain, from 1-32 (1, 2, 4, 8 recommended)
        
        Notes:
            Overwrites the casperfpga program method, which has been reproduced
            as _program

        """
        # Make a dictionary out of chips specified on command line.
        # mapping chip letters to numbers to facilitate writing to adc16_controller
        self.logger.info("Programming with %s - gain %i demux %i" % (boffile, gain, demux_mode))
        self.transport.program(boffile)

        if self.is_adc16_based():
            self.logger.info("Design is ADC16 based. Calibration routines will run.")

            # Check in case SnapAdc is already setup
            if self.uses_adc:
                if not isinstance(self.adc, SnapAdc):
                    self.adc = SnapAdc(self)
            self.fpga_set_demux(1)
            self.adc.set_chip_select(chips)
            self.adc.initialize()
            self.adc.set_demux(demux_mode)
            self.adc.set_gain(gain)
            self.adc.power_cycle()
            self.adc.calibrate()
        self.logger.info("Programming complete.")

    def upload_to_ram_and_program(self, filename, port=-1, timeout=10,
                                  wait_complete=True,
                                  gain=1, demux_mode=1, chips=('a', 'b', 'c')):
        """
        Upload an FPG file to RAM and then program the FPGA.
        :param filename: the file to upload
        :param port: the port to use on the rx end, -1 means a random port
        :param timeout: how long to wait, seconds
        :param wait_complete: wait for the transaction to complete, return
        after upload if False
        :return:
        """
        rv = self.transport.upload_to_ram_and_program(
            filename, port, timeout, wait_complete)
        if filename[-3:] == 'fpg':
            self.get_system_information(filename)

        if self.is_adc16_based():
            self.logger.info("Design is ADC16 based. Calibration routines will run.")

            # Check in case SnapAdc is already setup
            if self.uses_adc:
                if not isinstance(self.adc, SnapAdc):
                    self.adc = SnapAdc(self)
            self.fpga_set_demux(1)
            self.adc.set_chip_select(chips)
            self.adc.initialize()
            self.adc.set_demux(demux_mode)
            self.adc.set_gain(gain)
            self.adc.power_cycle()
            self.adc.calibrate()
        self.logger.info("Programming complete.")

        return rv

    def set_debug(self):
        """ Set logger levels to output debug info """
        self.logger.setLevel(5)
        if self.uses_adc:
            self.adc.logger.setLevel(5)

    def is_adc16_based(self):
        """ Check if design uses ADC16 chip """
        try:
            if 'adc16_controller' in self.listdev():
                return True
            else:
                return False
        except RuntimeError:
            return False

    def fpga_set_demux(self, fpga_demux):
        """ Set demux on FPGA

        Notes:
            Setting fpga demux rearranges the bits before they're output from the adc block depending on
            the adc demux mode used.
            State is assigned according to the adc16_controller memory map. (4+n) shifted by the amount of bits
            that precede the WMM field.
            4 always activates the W bit to allow writing to the MM bits and n is determined by the adc demux mode used
        """

        demux_shift = 24

        if fpga_demux == 1:
            state = (4 + 0) << demux_shift
            self.write_int('adc16_controller', state, word_offset=1, blindwrite=True)
        elif fpga_demux == 2:
            # writing the WW enable bit(4) as well as the demux setting bit(1 for demux mode 2
            # as seen in the adc16_controller memory map)
            state = (4 + 1) << demux_shift
            self.write_int('adc16_controller', state, word_offset=1, blindwrite=True)

        elif fpga_demux == 4:
            state = (4 + 2) << demux_shift
            self.write_int('adc16_controller', state, word_offset=1, blindwrite=True)
        else:
            self.logger.error('Invalid or no demux mode specified')
            raise RuntimeError('Invalid or no demux mode specified')

