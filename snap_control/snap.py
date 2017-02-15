"""
# adc16.py

Provides KATCP wrapper around ADC16-based CASPER design.  Includes many
convenience functions for writing to the registers of the ADC chips,
calibrating the SERDES blocks, and accessing status info about the ADC16
design and clock status.  While most access will be done via the methods of
this class, there may be occasion to access the ADC16 controller directly
(via the #adc16_controller method, which returns a KATCP::Bram object)

"""

import time
from . import katcp_wrapper
import numpy as np
import struct
import logging

katcp_port = 7147


# Here is the memory map for the underlying #adc16_controller device:
#
#   # ======================================= #
#   # ADC16 3-Wire Register (word 0)          #
#   # ======================================= #
#   # LL = Clock locked bits                  #
#   # NNNN = Number of ADC chips supported    #
#   # RR = ROACH2 revision expected/required  #
#   # C = SCLK                                #
#   # D = SDATA                               #
#   # 7 = CSNH (chip select H, active high)   #
#   # 6 = CSNG (chip select G, active high)   #
#   # 5 = CSNF (chip select F, active high)   #
#   # 4 = CSNE (chip select E, active high)   #
#   # 3 = CSND (chip select D, active high)   #
#   # 2 = CSNC (chip select C, active high)   #
#   # 1 = CSNB (chip select B, active high)   #
#   # 0 = CSNA (chip select A, active high)   #
#   # ======================================= #
#   # |<-- MSb                       LSb -->| #
#   # 0000_0000_0011_1111_1111_2222_2222_2233 #
#   # 0123_4567_8901_2345_6789_0123_4567_8901 #
#   # ---- --LL ---- ---- ---- ---- ---- ---- #
#   # ---- ---- NNNN ---- ---- ---- ---- ---- #
#   # ---- ---- ---- --RR ---- ---- ---- ---- #
#   # ---- ---- ---- ---- ---- --C- ---- ---- #
#   # ---- ---- ---- ---- ---- ---D ---- ---- #
#   # ---- ---- ---- ---- ---- ---- 7654 3210 #
#   # |<--- Status ---->| |<--- 3-Wire ---->| #
#   # ======================================= #
#   # NOTE: LL reflects the runtime lock      #
#   #       status of a line clock from each  #
#   #       ADC board.  A '1' bit means       #
#   #       locked (good!).  Bit 5 is always  #
#   #       used, but bit 6 is only used when #
#   #       NNNN is 4 (or less).              #
#   # ======================================= #
#   # NOTE: NNNN and RR are read-only values  #
#   #       that are set at compile time.     #
#   #       They do not indicate the state    #
#   #       of the actual hardware in use     #
#   #       at runtime.                       #
#   # ======================================= #
#
#   # ======================================= #
#   # ADC16 Control Register (word 1)         #
#   # ======================================= #
#   # W  = Deux write-enable                  #
#   # MM = Demux mode                         #
#   # R = ADC16 Reset                         #
#   # S = Snap Request                        #
#   # H = ISERDES Bit Slip Chip H             #
#   # G = ISERDES Bit Slip Chip G             #
#   # F = ISERDES Bit Slip Chip F             #
#   # E = ISERDES Bit Slip Chip E             #
#   # D = ISERDES Bit Slip Chip D             #
#   # C = ISERDES Bit Slip Chip C             #
#   # B = ISERDES Bit Slip Chip B             #
#   # A = ISERDES Bit Slip Chip A             #
#   # T = Delay Tap
#   # i = Bitslip specific channel(out of 8)  #
#   # ======================================= #
#   # |<-- MSb                       LSb -->| #
#   # 0000 0000 0011 1111 1111 2222 2222 2233 #
#   # 0123 4567 8901 2345 6789 0123 4567 8901 #
#   # ---- -WMM ---- ---- ---- ---- ---- ---- #
#   # ---- ---- ---R ---- ---- ---- ---- ---- #
#   # ---- ---- ---- ---S ---- ---- ---- ---- #
#   # ---- ---- ---- ---- HGFE DCBA iii- ---- #
#   # ---- ---- ---- ---- ---- ---- ---T TTTT #
#   # ======================================= #
#   # NOTE: W enables writing the MM bits.    #
#   #       Some of the other bits in this    #
#   #       register are one-hot.  Using      #
#   #       W ensures that the MM bits will   #
#   #       only be written to when desired.  #
#   #       00: demux by 1 (single channel)   #
#   # ======================================= #
#   # NOTE: MM selects the demux mode.        #
#   #       00: demux by 1 (quad channel)     #
#   #       01: demux by 2 (dual channel)     #
#   #       10: demux by 4 (single channel)   #
#   #       11: undefined                     #
#   #       ADC board.  A '1' bit means       #
#   #       locked (good!).  Bit 5 is always  #
#   #       used, but bit 6 is only used when #
#   #       NNNN is 4 (or less).              #
#   # ======================================= #
#
#   # =============================================== #
#   # ADC16 Delay A Strobe Register (word 2)          #
#   # =============================================== #
#   # D = Delay Strobe (rising edge active)           #
#   # =============================================== #
#   # |<-- MSb                              LSb -->|  #
#   # 0000  0000  0011  1111  1111  2222  2222  2233  #
#   # 0123  4567  8901  2345  6789  0123  4567  8901  #
#   # DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  #
#   # |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  #
#   # H4 H1 G4 G1 F4 F1 E4 E1 D4 D1 C4 C1 B4 B1 A4 A1 #
#   # =============================================== #
#
#   # =============================================== #
#   # ADC0 Delay B Strobe Register (word 3)           #
#   # =============================================== #
#   # D = Delay Strobe (rising edge active)           #
#   # =============================================== #
#   # |<-- MSb                              LSb -->|  #
#   # 0000  0000  0011  1111  1111  2222  2222  2233  #
#   # 0123  4567  8901  2345  6789  0123  4567  8901  #
#   # DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  #
#   # |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  #
#   # H4 H1 G4 G1 F4 F1 E4 E1 D4 D1 C4 C1 B4 B1 A4 A1 #
#   # =============================================== #



class SnapBoard(katcp_wrapper.FpgaClient):
    """
    Construct an snap_control instance. allowed kwargs are

    hostname
    katcp_port
    timeout
    test_pattern
    demux_mode
    gain
    chips
    """
    def __init__(self, hostname, katcp_port=7147, timeout=10, 
                 verbose=False, **kwargs):
        super(SnapBoard, self).__init__(hostname, katcp_port, timeout)

        if verbose == True:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        # create a chip dictionary to facilitate writing to adc16_controller
        self.chips = {}
        self.demux_mode    = None
        self.gain          = None
        self.chip_select   = None


    def set_chip_select(self, chips):
        """ Setup which chips will be used in the programmed design

        update chip dictionary to facilitate writing to adc16_controller

        Args:
            chips (list): list of chips, ['a', 'b', 'c']
        """
        chip_select_a = 0
        chip_select_b = 0
        chip_select_c = 0
        for chip in chips:
            chip = chip.lower()
            if chip == 'a':
                self.chips['a'] = 0
                chip_select_a = 1 << self.chips['a']
            elif chip == 'b':
                self.chips['b'] = 1
                chip_select_b = 1 << self.chips['b']
            elif chip == 'c':
                self.chips['c'] = 2
                chip_select_c = 1 << self.chips['c']
            else:
                logging.error('Invalid chip name passed, available values: a, b or c, default is all chips selected')
                exit(1)
        self.chip_select = chip_select_a | chip_select_b | chip_select_c

    def program(self, boffile, gain=1, demux_mode=1, chips=['a', 'b', 'c']): 
        """ Reprogram the FPGA with a given boffile AND calibrates

        Adds gain, demux_mode and chips params to katcp_wrapper's progdev

        Args:
            boffile (str): Name of boffile to program
            gain (int): ADC gain, from 1-32 (1, 2, 4, 8 recommended)

        """
        # Make a dictionary out of chips specified on command line.
        # mapping chip letters to numbers to facilitate writing to adc16_controller
        self.progdev(boffile)

        if self.adc16_based():
            self.set_demux_adc(demux_mode)
            self.gain         = gain
            self.set_chip_select(chips)
            self.calibrate()

    def write_adc(self, addr, data):
        """
        # write_adc is used for writing specific ADC registers.
        # ADC controller can only write to adc one bit at a time at rising clock edge
        """
        SCLK = 0x200
        CS = self.chip_select
        IDLE = SCLK
        SDA_SHIFT = 8
        self.write_int('adc16_controller', IDLE, offset=0, blindwrite=True)
        for i in range(8):
            addr_bit = (addr >> (8 - i - 1)) & 1
            state = (addr_bit << SDA_SHIFT) | CS
            self.write_int('adc16_controller', state, offset=0, blindwrite=True)
            logging.debug("Printing address state written to adc16_controller, offset=0, clock low")
            logging.debug(np.binary_repr(state, width=32))
            state = (addr_bit << SDA_SHIFT) | CS | SCLK
            self.write_int('adc16_controller', state, offset=0, blindwrite=True)
            logging.debug("Printing address state written to adc16_controller, offset=0, clock high")
            logging.debug(np.binary_repr(state, width=32))

        for j in range(16):
            data_bit = (data >> (16 - j - 1)) & 1
            state = (data_bit << SDA_SHIFT) | CS
            self.write_int('adc16_controller', state, offset=0, blindwrite=True)
            logging.debug("Printing data state written to adc16_controller, offset=0, clock low")
            logging.debug(np.binary_repr(state, width=32))
            state = (data_bit << SDA_SHIFT) | CS | SCLK
            self.write_int('adc16_controller', state, offset=0, blindwrite=True)
            logging.debug("Printing data address state written to adc16_controller, offset=0, clock high")
            logging.debug(np.binary_repr(state, width=32))

        self.write_int('adc16_controller', IDLE, offset=0, blindwrite=True)

    def power_cycle(self):
        """ Power cycle the ADC """
        logging.info('Power cycling the ADC')
        # power adc down
        self.write_adc(0x0f, 0x0200)
        # power adc up
        self.write_adc(0x0f, 0x0000)

    def adc_reset(self):
        """ Reset the ADC """
        logging.info('Initializing ADC')
        # reset adc
        self.write_adc(0x00, 0x0001)

    def adc_initialize(self):
        """ Initialize the ADC  """
        self.adc_reset()
        # power adc down
        self.write_adc(0x0f, 0x0200)
        # select operating mode
        self.set_demux_adc()
        # power adc up
        self.write_adc(0x0f, 0x0000)

    def set_demux_adc(self, demux_mode):
        """ Set demux factor for ADC mode

        Interleave all inputs: demux=4
        No interleaving: demux=1
        Interleaving ADC0 and ADC2: demux=2

        Args:
            demux_mode (int): Set demulitplexing to 1 (no interleave), 2 or 4 (interleave all)
        """
        self.demux_mode = demux_mode
        if self.demux_mode == 1:
            # Setting number of channes to 4
            self.write_adc(0x31, 0x04)
            # Route inputs to respective ADC's for demux 1
            print('Routing all four inputs to corresponding ADC channels')
            self.write_adc(0x3a, 0x0402)
            self.write_adc(0x3b, 0x1008)
        elif self.demux_mode == 2:
            # Setting number of channels to 2
            self.write_adc(0x31, 0x02)
            # Routing input 1 and input 3 to ADC for interleaving
            print('Setting ADC to interleave inputs 1 (ADC0) and 3 (ADC2)')
            # Selecting input 1
            self.write_adc(0x3a, 0x0202)
            # Selecting input 3
            self.write_adc(0x3b, 0x0808)
        elif self.demux_mode == 4:
            # Setting the number of channels to 1
            self.write_adc(0x31, 0x01)
            print('Setting ADC to interleave input (ADC0)')
            # Selecting input 1
            self.write_adc(0x3a, 0x0202)
            self.write_adc(0x3b, 0x0202)
        else:
            logging.error('demux_mode variable not assigned. Weird.')
            exit(1)


    def set_demux_fpga(self, fpga_demux):
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
            self.write_int('adc16_controller', state, offset=1, blindwrite=True)
        elif fpga_demux == 2:
            # writing the WW enable bit(4) as well as the demux setting bit(1 for demux mode 2
            # as seen in the adc16_controller memory map)
            state = (4 + 1) << demux_shift
            self.write_int('adc16_controller', state, offset=1, blindwrite=True)

        elif fpga_demux == 4:
            state = (4 + 2) << demux_shift
            self.write_int('adc16_controller', state, offset=1, blindwrite=True)
        else:
            print('Invalid or no demux mode specified')
            exit(1)


    def adc16_based(self):
        """ Check if design uses ADC16 chip """
        if 'adc16_controller' in self.listdev():
            print('Design is ADC16-based')
        else:
            print('Design is not ADC16-based')
            exit(1)



    def enable_pattern(self, pattern):
        """

        Args:
            pattern (str): select a test pattern (ramp, deskew, sync, none, ...).
                           see list in notes for more details



        Notes
             Selects a test pattern or sampled data for all ADCs selected by
             +chip_select+.  +ptn+ can be any of:

               :ramp            Ramp pattern 0-255
               :deskew (:eye)   Deskew pattern (10101010)
               :sync (:frame)   Sync pattern (11110000)
               :custom1         Custom1 pattern
               :custom2         Custom2 pattern
               :dual            Dual custom pattern
               :none            No pattern (sampled data)

             Default is :ramp.  Any value other than shown above is the same as :none
             (i.e. pass through sampled data)
        """
        self.write_adc(0x25, 0x00)
        self.write_adc(0x45, 0x00)
        if pattern == 'ramp':
            self.write_adc(0x25, 0x0040)
        elif pattern == 'deskew':
            self.write_adc(0x45, 0x0001)
        elif pattern == 'sync':
            self.write_adc(0x45, 0x0002)
        else:
            print('Invalid test pattern selected')
            exit(1)
        # else:
        #			self.write_adc(0x25,0x10)
        #			self.write_adc(0x26,(self.expected)<<8)
        time.sleep(1)

    def read_ram(self, device):
        SNAP_REQ = 0x00010000
        self.write_int('adc16_controller', 0, offset=1, blindwrite=True)
        self.write_int('adc16_controller', SNAP_REQ, offset=1, blindwrite=True)
        # Read the device that is passed to the read_ram method,1024 elements at a time,
        # snapshot is a binary string that needs to get unpacked
        # Part of the read request is the size parameter,1024, which specifies the
        # amount of bytes to read form the device
        snapshot = self.read(device, 1024, offset=0)

        # struct unpack returns a tuple of signed int values.
        # Since we're requesting to read adc16_wb_ram at a size of 1024 bytes, we are unpacking
        # 1024 bytes each of which is a signed char(in C, python only knows ints). Unpacking as
        # a signed char is for mapping purposes:

        # ADC returns values from 0 to 255 (since it's an 8 bit ADC), the voltage going into ADC
        # varies from -1V to 1V, we want 0 to mean 0, not -1 volts so we need to remap the output
        # of the ADC to something more sensible, like -128 to 127. That way 0 volts corresponds to
        # a 0 value in the unpacked data.
        string_data = struct.unpack('>1024b', snapshot)
        # Converting the tuple into a vector of 1024 elements
        array_data = np.array(string_data)
        #		for i in range(array_data.shape[0]):
        #			print('{:08b}'.format(array_data[i]))
        # print(array_data)
        return array_data




    def bitslip(self, chip_num, channel):
        """
        The ADC16 controller word (the offset in write_int method) 2 and 3 are for delaying taps of
        A and B lanes, respectively.
        Refer to the memory map word 2 and word 3 for clarification. The memory map was made for a
        ROACH design so it has chips A-H. SNAP 1 design has three chips
        """
        chan_shift = 5
        chan_select_bs = channel << chan_shift
        state = 0
        chip_shift = 8
        chip_select_bs = 1 << chip_shift + chip_num
        state = (chip_select_bs | chan_select_bs)
        #		print('Bitslip state written to offset=1:',bin(state))
        self.write_int('adc16_controller', 0, offset=1, blindwrite=True)
        self.write_int('adc16_controller', state, offset=1, blindwrite=True)
        #	regvalue=self.read('adc16_controller', 32, offset=1)
        #	print('Bitslip Reg Value\n')
        #	print(struct.unpack('>32b', regvalue))
        self.write_int('adc16_controller', 0, offset=1, blindwrite=True)

    def delay_tap(self, tap, channel, chip_num):

        if channel == 'all':
            chan_select = (0xf << (chip_num * 4))

            delay_tap_mask = 0x1f
            self.write_int('adc16_controller', 0, offset=2, blindwrite=True)
            self.write_int('adc16_controller', 0, offset=3, blindwrite=True)
            # Set tap bits
            self.write_int('adc16_controller', delay_tap_mask & tap, offset=1, blindwrite=True)
            # Set strobe bits
            self.write_int('adc16_controller', chan_select, offset=2, blindwrite=True)
            self.write_int('adc16_controller', chan_select, offset=3, blindwrite=True)
            # Clear all bits
            self.write_int('adc16_controller', 0, offset=1, blindwrite=True)
            self.write_int('adc16_controller', 0, offset=2, blindwrite=True)
            self.write_int('adc16_controller', 0, offset=3, blindwrite=True)
            # Note this return statement, after all channels have been bitslip it'll exit out of the function.
            # the function is called again after figuring out the best tap with a single channel argument.
            return
        elif channel == '1a':
            chan_select = 0x1 << (chip_num * 4)
            lane_offset = 2
        elif channel == '1b':
            chan_select = 0x1 << (chip_num * 4)
            lane_offset = 3
        elif channel == '2a':
            chan_select = 0x2 << (chip_num * 4)
            lane_offset = 2
        elif channel == '2b':
            chan_select = 0x2 << (chip_num * 4)
            lane_offset = 3
        elif channel == '3a':
            chan_select = 0x4 << (chip_num * 4)
            lane_offset = 2
        elif channel == '3b':
            chan_select = 0x4 << (chip_num * 4)
            lane_offset = 3
        elif channel == '4a':
            chan_select = 0x8 << (chip_num * 4)
            lane_offset = 2
        elif channel == '4b':
            chan_select = 0x8 << (chip_num * 4)
            lane_offset = 3

        delay_tap_mask = 0x1f
        self.write_int('adc16_controller', 0, offset=lane_offset, blindwrite=True)
        # Set tap bits
        self.write_int('adc16_controller', delay_tap_mask & tap, offset=1, blindwrite=True)
        # Set strobe bits
        self.write_int('adc16_controller', chan_select, offset=lane_offset, blindwrite=True)
        # Clear all bits
        self.write_int('adc16_controller', 0, offset=1, blindwrite=True)
        self.write_int('adc16_controller', 0, offset=2, blindwrite=True)
        self.write_int('adc16_controller', 0, offset=3, blindwrite=True)


    def test_tap(self, chip_num, taps):
        """
        returns an array of error counts for a given tap(assume structure chan 1a, chan 1b, chan 2a, chan 2b etc.. until chan 4b
        taps argument can have a value of an int or a string. If it's a string then it will iterate through all 32 taps
        if it's an int it will only delay all channels by that particular tap value.
        """

        if taps == 'all':

            error_count = []
            # read_ram reuturns an array of data form a sanpshot from ADC output
            for tap in range(32):

                self.delay_tap(tap, 'all', chip_num)
                data = self.read_ram('adc16_wb_ram{0}'.format(chip_num))
                # each tap will return an error count for each channel and lane, so an array of 8 elements with an error count for each

                chan1a_error = 0
                chan1b_error = 0
                chan2a_error = 0
                chan2b_error = 0
                chan3a_error = 0
                chan3b_error = 0
                chan4a_error = 0
                chan4b_error = 0

                i = 0
                while i < 1024:
                    if data[i] != 0x2a:
                        chan1a_error += 1
                    if data[i + 1] != 0x2a:
                        chan1b_error += 1
                    if data[i + 2] != 0x2a:
                        chan2a_error += 1
                    if data[i + 3] != 0x2a:
                        chan2b_error += 1
                    if data[i + 4] != 0x2a:
                        chan3a_error += 1

                    if data[i + 5] != 0x2a:
                        chan3b_error += 1
                    if data[i + 6] != 0x2a:
                        chan4a_error += 1
                    if data[i + 7] != 0x2a:
                        chan4b_error += 1
                    i += 8

                error_count.append(
                    [chan1a_error, chan1b_error, chan2a_error, chan2b_error, chan3a_error, chan3b_error, chan4a_error,
                     chan4b_error])
            return (error_count)
        else:

            error_count = []
            # read_ram reuturns an array of data form a sanpshot from ADC output

            self.delay_tap(taps, 'all', chip_num)
            data = self.read_ram('adc16_wb_ram{0}'.format(chip_num))
            # each tap will return an error count for each channel and lane, so an array of 8 elements with an error count for each

            chan1a_error = 0
            chan1b_error = 0
            chan2a_error = 0
            chan2b_error = 0
            chan3a_error = 0
            chan3b_error = 0
            chan4a_error = 0
            chan4b_error = 0

            i = 0
            while i < 1024:
                if data[i] != 0x2a:
                    chan1a_error += 1
                if data[i + 1] != 0x2a:
                    chan1b_error += 1
                if data[i + 2] != 0x2a:
                    chan2a_error += 1
                if data[i + 3] != 0x2a:
                    chan2b_error += 1
                if data[i + 4] != 0x2a:
                    chan3a_error += 1

                if data[i + 5] != 0x2a:
                    chan3b_error += 1
                if data[i + 6] != 0x2a:
                    chan4a_error += 1
                if data[i + 7] != 0x2a:
                    chan4b_error += 1
                i += 8

            error_count.append(
                [chan1a_error, chan1b_error, chan2a_error, chan2b_error, chan3a_error, chan3b_error, chan4a_error,
                 chan4b_error])
            logging.debug('Error count for {0} tap: {1}'.format(taps, error_count))
            return (error_count)

    def walk_taps(self):
        for chip, chip_num in self.chips.iteritems():
            # Set demux 4 on the FPGA side (just rearranging outputs as opposed to dividing clock and assigning channels)
            self.set_demux_fpga(4)

            print('Calibrating chip %s...' % chip)
            logging.debug('Setting deskew pattern...')
            logging.debug('Stuff in chip %s before enabling pattern' % chip)
            logging.debug(self.read_ram('adc16_wb_ram{0}'.format(chip_num)))
            self.enable_pattern('deskew')
            logging.debug('Stuff in chip after enabling test mode\n')
            logging.debug(self.read_ram('adc16_wb_ram{0}'.format(chip_num)))

            logging.debug('Taps before bitslipping anything\n')
            logging.debug(self.test_tap(chip_num, 'all'))
            # check if either of the extreme tap setting returns zero errors in any one of the channels. Bitslip if True.
            # This is to make sure that the eye of the pattern is swept completely
            error_counts_0 = self.test_tap(chip_num, 0)
            error_counts_31 = self.test_tap(chip_num, 31)
            for i in range(8):
                if not (error_counts_0[0][i]) or not (error_counts_31[0][i]):
                    logging.debug('Bitslipping chan %i' % i)
                    self.bitslip(chip_num, i)
                    error_counts_0 = self.test_tap(chip_num, 0)
                    error_counts_31 = self.test_tap(chip_num, 31)

            # error_list is a list of 32 'rows'(corresponding to the 32 taps) , each row containing 8 elements,each element is the number of errors
            # of that lane  when compared to the expected value. read_ram method unpacks 1024 bytes. There are 8
            # lanes so each lane gets 1024/8=128 read outs from a single call to read_ram method, like this, channel_1a etc. represent the errors in that channel
            # tap 0: [ channel_1a channel_1b channel_2a channel_2b channel_3a channel_3b channel_4a channel_4b]
            # tap 1: [ channel_1a channel_1b channel_2a channel_2b channel_3a channel_3b channel_4a channel_4b]
            # .....: [ channel_1a channel_1b channel_2a channel_2b channel_3a channel_3b channel_4a channel_4b]
            # tap 31:[ channel_1a channel_1b channel_2a channel_2b channel_3a channel_3b channel_4a channel_4b]
            error_list = self.test_tap(chip_num, 'all')
            good_tap_range = []
            best_tap_range = []
            logging.debug('Printing the list of errors, each row is a tap\n')
            logging.debug(['chan1a', 'chan1b', 'chan2a', 'chan2b', 'chan3a', 'chan3b', 'chan4a', 'chan4b'])
            logging.debug(error_list)
            min_tap = []
            max_tap = []
            # This loop goes through error_list, finds the elements with a value of 0 and appends them to the good tap range list
            # It also picks out the elements corresponding to different channels and groups them together. The error_list is a list where each 'row' is a different tap
            # I wanted to find the elements in each channel that have zero errors, group the individual channels, and get the value of the tap in which they're in - which is the index of the row
            for i in range(8):
                good_tap_range.append([])
                # j represents the tap value
                for j in range(32):
                    # i represents the channel/lane value
                    if error_list[j][i] == 0:
                        good_tap_range[i].append(j)
                        #	find the min and max of each element of good tap range and call delay tap
            logging.debug('Printing good tap values for each channel...each row corresponds to different channel')

            for i in range(len(good_tap_range)):
                logging.debug('Channel {0}: {1}'.format(i + 1, good_tap_range[i]))

            channels = ['1a', '1b', '2a', '2b', '3a', '3b', '4a', '4b']
            for k in range(8):
                min_tap = min(good_tap_range[k])
                max_tap = max(good_tap_range[k])

                best_tap = (min_tap + max_tap) // 2
                self.delay_tap(best_tap, channels[k], chip_num)
            logging.debug('Printing the calibrated data from ram{0}.....'.format(self.chips[chip]))
            logging.debug(self.read_ram('adc16_wb_ram{0}'.format(self.chips[chip])))

            # Bitslip channels until the sync pattern is captured
            self.sync_chips(chip_num)

    def sync_chips(self, chip_num):
        """ Synchronize chips with bitslip """
        # channels = {0:'1a',1:'1b',2:'2a',3:'2b',4:'3a',5:'3b',6:'4a',7:'4b'}
        self.enable_pattern('sync')

        snap = self.read_ram('adc16_wb_ram{0}'.format(chip_num))
        logging.debug('Snapshot before bitslipping:\n')
        logging.debug(snap[0:8])

        for i in range(8):
            loop_ctl = 0
            while snap[i] != 0x70:
                logging.debug('Bitsliping channel %i\n' % i)
                self.bitslip(chip_num, i)
                snap = self.read_ram('adc16_wb_ram{0}'.format(chip_num))
                logging.debug('Snapshot after bitslipping:\n')
                logging.debug(snap[0:8])
                loop_ctl += 1
                if loop_ctl > 10:
                    print(
                        "It appears that bitslipping is not working, make sure you're using the version of Jasper library")
                    exit(1)

    def clock_locked(self):
        """ Check if CLK is locked """
        locked_bit = self.read_int('adc16_controller', offset=0) >> 24
        if locked_bit & 3:
            logging.info('ADC clock is locked!!!')
            print(self.est_brd_clk())
        else:
            logging.error('ADC clock not locked, check your clock source/correctly set demux mode')
            exit(1)

    def clear_pattern(self):
        """Clears test pattern from ADCs"""
        self.write_adc(0x25, 0x00)
        self.write_adc(0x45, 0x00)

    def set_gain(self):
        """ Set gain value on ADCs"""
        if self.demux_mode == 1:
            self.write_adc(0x2a, self.gain * 0x1111)
        elif self.demux_mode == 2:
            self.write_adc(0x2b, self.gain * 0x0011)
        elif self.demux_mode == 4:
            self.write_adc(0x2b, self.gain * 0x0100)
        else:
            print('demux mode is not set')
            exit(1)

    def calibrate(self):
        """" Run calibration routines """
        self.adc_initialize()
        # check if clock is locked
        self.clock_locked()
        # check if design is ADC16 based
        self.adc16_based()
        # Setting gain value, default is 1
        self.set_gain()
        # Calibrate ADC by going through various tap values
        self.walk_taps()
        # Clear pattern setting registers so real data could be taken
        self.clear_pattern()
        print('Setting fpga demux to %i' % self.demux_mode)
        self.set_demux_fpga(self.demux_mode)