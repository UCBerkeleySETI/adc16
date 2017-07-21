"""
# snap_adc.py

A controller for the three HMCAD1511 ADC chips on the CASPER SNAP board.

This requires a 'host' SnapBoard() object to which it attaches:

    ```
    s = SnapBoard('board_name')
    s.adc   <--- This is a SnapAdc object
    ```

HMCAD1511 datasheet can be found at:
https://casper.berkeley.edu/wiki/images/0/05/Hittite_hmcad1511.pdf

## ADC16 controller memory map

   # ======================================= #             # ======================================= #
   # ADC16 3-Wire Register (word 0)          #             # ADC16 Control Register (word 1)         #
   # ======================================= #             # ======================================= #
   # LL = Clock locked bits                  #             # W  = Deux write-enable                  #
   # NNNN = Number of ADC chips supported    #             # MM = Demux mode                         #
   # RR = ROACH2 revision expected/required  #             # R = ADC16 Reset                         #
   # C = SCLK                                #             # S = Snap Request                        #
   # D = SDATA                               #             # H = ISERDES Bit Slip Chip H             #
   # 7 = CSNH (chip select H, active high)   #             # G = ISERDES Bit Slip Chip G             #
   # 6 = CSNG (chip select G, active high)   #             # F = ISERDES Bit Slip Chip F             #
   # 5 = CSNF (chip select F, active high)   #             # E = ISERDES Bit Slip Chip E             #
   # 4 = CSNE (chip select E, active high)   #             # D = ISERDES Bit Slip Chip D             #
   # 3 = CSND (chip select D, active high)   #             # C = ISERDES Bit Slip Chip C             #
   # 2 = CSNC (chip select C, active high)   #             # B = ISERDES Bit Slip Chip B             #
   # 1 = CSNB (chip select B, active high)   #             # A = ISERDES Bit Slip Chip A             #
   # 0 = CSNA (chip select A, active high)   #             # T = Delay Tap
   # ======================================= #             # i = Bitslip specific channel(out of 8)  #
   # |<-- MSb                       LSb -->| #             # ======================================= #
   # 0000_0000_0011_1111_1111_2222_2222_2233 #             # |<-- MSb                       LSb -->| #
   # 0123_4567_8901_2345_6789_0123_4567_8901 #             # 0000 0000 0011 1111 1111 2222 2222 2233 #
   # ---- --LL ---- ---- ---- ---- ---- ---- #             # 0123 4567 8901 2345 6789 0123 4567 8901 #
   # ---- ---- NNNN ---- ---- ---- ---- ---- #             # ---- -WMM ---- ---- ---- ---- ---- ---- #
   # ---- ---- ---- --RR ---- ---- ---- ---- #             # ---- ---- ---R ---- ---- ---- ---- ---- #
   # ---- ---- ---- ---- ---- --C- ---- ---- #             # ---- ---- ---- ---S ---- ---- ---- ---- #
   # ---- ---- ---- ---- ---- ---D ---- ---- #             # ---- ---- ---- ---- HGFE DCBA iii- ---- #
   # ---- ---- ---- ---- ---- ---- 7654 3210 #             # ---- ---- ---- ---- ---- ---- ---T TTTT #
   # |<--- Status ---->| |<--- 3-Wire ---->| #             # ======================================= #
   # ======================================= #             # NOTE: W enables writing the MM bits.    #
   # NOTE: LL reflects the runtime lock      #             #       Some of the other bits in this    #
   #       status of a line clock from each  #             #       register are one-hot.  Using      #
   #       ADC board.  A '1' bit means       #             #       W ensures that the MM bits will   #
   #       locked (good!).  Bit 5 is always  #             #       only be written to when desired.  #
   #       used, but bit 6 is only used when #             #       00: demux by 1 (single channel)   #
   #       NNNN is 4 (or less).              #             # ======================================= #
   # ======================================= #             # NOTE: MM selects the demux mode.        #
   # NOTE: NNNN and RR are read-only values  #             #       00: demux by 1 (quad channel)     #
   #       that are set at compile time.     #             #       01: demux by 2 (dual channel)     #
   #       They do not indicate the state    #             #       10: demux by 4 (single channel)   #
   #       of the actual hardware in use     #             #       11: undefined                     #
   #       at runtime.                       #             #       ADC board.  A '1' bit means       #
   # ======================================= #             #       locked (good!).  Bit 5 is always  #
                                                           #       used, but bit 6 is only used when #
                                                           #       NNNN is 4 (or less).              #
                                                           # ======================================= #


   # =============================================== #     # =============================================== #
   # ADC16 Delay A Strobe Register (word 2)          #     # ADC0 Delay B Strobe Register (word 3)           #
   # =============================================== #     # =============================================== #
   # D = Delay Strobe (rising edge active)           #     # D = Delay Strobe (rising edge active)           #
   # =============================================== #     # =============================================== #
   # |<-- MSb                              LSb -->|  #     # |<-- MSb                              LSb -->|  #
   # 0000  0000  0011  1111  1111  2222  2222  2233  #     # 0000  0000  0011  1111  1111  2222  2222  2233  #
   # 0123  4567  8901  2345  6789  0123  4567  8901  #     # 0123  4567  8901  2345  6789  0123  4567  8901  #
   # DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  #     # DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  #
   # |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  #     # |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  #
   # H4 H1 G4 G1 F4 F1 E4 E1 D4 D1 C4 C1 B4 B1 A4 A1 #     # H4 H1 G4 G1 F4 F1 E4 E1 D4 D1 C4 C1 B4 B1 A4 A1 #
   # =============================================== #     # =============================================== #


"""



import logging
import struct
import time

import numpy as np
from pkg_resources import resource_filename


# Notes:
# Load ADC MAP (Table 5 in HMCAD1511 spec sheet)
ADC_MAP_TXT = resource_filename("snap_control", "adc_register_map.txt")


# Notes:
# Table 8 from HMCAD1511 spec sheet: Input select
# -------------------------------------------
# | inp_sel_adcx <4:0>     | selected input |
# | 0001 0                 | IN1            |
# | 0010 0                 | IN2            |
# | 0100 0                 | IN3            |
# | 1000 0                 | IN4            |
# -------------------------------------------

INPUT_MAP  = {1: 0b00010,
              2: 0b00100,
              3: 0b01000,
              4: 0b10000}

def generate_adc_map():
    """ Generate ADC map from text file """
    d = np.genfromtxt(ADC_MAP_TXT, delimiter='|', skip_header=2, dtype='str')
    ADC_MAP = {}

    class AdcRegister(object):
        """ Simple object to store ADC register information.

        AdcRegister(name, hex_addr, width, offset, description)
            name: name of register
            hex_addr: Address of register word in hexadecimal (hex or int)
            width: width of register (int)
            offset: offset of register within hex word (int)
            description: textual description of register (string)
        """
        def __init__(self, name, hex_addr, width, offset, description):
            self.name   = name.strip()
            if isinstance(hex_addr, int):
                self.addr   = hex_addr
            else:
                self.addr   = int(hex_addr, 16)
            self.width  = int(width)
            self.offset = int(offset)
            self.description = description.strip()

        def __repr__(self):
            return "<AdcRegister: %s>" % self.name

    for name, hex_addr, width, offset, description in d:
        ADC_MAP[name.strip()] = AdcRegister(name, hex_addr, width, offset, description)

    return ADC_MAP

class GenericAdc(object):
    """ Stand-in for generic ADCs """
    def __repr__(self):
        return "<SNAP generic ADC controller on %s>" % self.host.host

    def __init__(self, host):
        self.host = host
        self.logger = logging.getLogger('SnapAdc')


class SnapAdc(object):
    """" Controller for HMCAD1511 ADC chip, as used in CASPER SNAP and ROACH2 boards

    Provides control and calibration routines for the HMCAD1511.

    Args:
        host (SnapBoard object): Instance which has the adc16_controller

    """

    def __repr__(self):
        return "<SNAP HMCAD1511 8-bit ADC controller on %s>" % self.host.host

    def __init__(self, host):
        self.host = host

        # create a chip dictionary to facilitate writing to adc16_controller
        self.demux_mode    = 1              # Default to non-interleaved
        self.gain          = 1              # Default to gain of 1
        self.chip_select   = 7              # Default to select all chips
        self.chips = {'a': 0, 'b': 1, 'c': 2}
        self.ADC_MAP = generate_adc_map()
        self.INPUT_MAP = INPUT_MAP
        self.control_register = 'adc16_controller'

        self.logger = logging.getLogger('SnapAdc')

    def set_chip_select(self, chips):
        """ Setup which chips will be used in the programmed design

        Notes:
            update chip dictionary to facilitate writing to adc16_controller. This creates
            a self.chips dictionary and a self.chip_select which are used to tell if a
            given chip is enabled.

        Args:
            chips (list or str): list of chips, ['a', 'b', 'c'] or 'all', 'a', 'b' or 'c'
        """
        if isinstance(chips, str):
            if chips == 'all':
                self.chip_select = 0b111
                self.chips = {'a': 0, 'b': 1, 'c': 2}
            elif chips == 'a':
                self.chip_select = 0b001
                self.chips = {'a': 0}
            elif chips == 'b':
                self.chip_select = 0b010
                self.chips = {'b': 1}
            elif chips == 'c':
                self.chip_select = 0b100
                self.chips = {'c': 2}
        else:
            if 'all' in chips:
                self.chip_select = 0b111
                self.chips = {'a': 0, 'b': 1, 'c': 2}
            else:
                self.chips = {}
                chip_a, chip_b, chip_c = 0, 0, 0
                if 'a' in chips:
                    chip_a = 1
                    self.chips['a'] = 0
                if 'b' in chips:
                    chip_b = 1
                    self.chips['b'] = 1
                if 'c' in chips:
                    chip_c = 1
                    self.chips['c'] = 2
                self.chip_select = int('0b%i%i%i' % (chip_a, chip_b, chip_c), 2)

    def write_register(self, register, value):
        """ Write register with value

        Looks up the hex address and offset of the register, then
        writes the value with appropriate offsets.

        Args:
            register (str): register name
            value (int/bin/hex): Value to write to register

        Notes:
            This will override any other register that shares the hex address.
        """
        r = self.ADC_MAP[register]
        try:
            assert value <= (2**r.width - 1)
        except AssertionError:
            raise RuntimeError("Value %i is wider than address width of %i" % (value, r.width))

        r_val = value << r.offset
        self.write(r.addr, r_val)

    def write_shared_registers(self, regdict):
        """ Write multiple registers to one hex address at once.

        As with write_register, but takes dictionary for multiple registers
        residing within the same hex address.

        Args:
            regdict (dict): Dictionary of register_name : value pairs
        """
        hex_addr = None
        shared_val = 0
        for regname, regvalue in regdict.items():
            r = self.ADC_MAP[regname]
            if hex_addr is None:
                hex_addr = r.addr
            # Make sure all registers are valid and share hex address
            try:
                assert hex_addr == r.addr
            except AssertionError:
                raise RuntimeError("All registers must reside in same hex address.")
            try:
                assert regvalue <= (2**r.width - 1)
            except AssertionError:
                raise RuntimeError("Value %i is wider than address width of %i" % (regvalue, r.width))
            r_val = regvalue << r.offset
            shared_val += r_val     # As they're all offset you can just add 'em together

        self.write(r.addr, shared_val)

    def _write(self, value, word_offset=0, blindwrite=True):
        """ Write value to control register """
        self.host.write_int(self.control_register, value,
                            word_offset=word_offset, blindwrite=blindwrite)


    def write(self, addr, data):
        """
        # write_adc is used for writing specific ADC registers.
        # ADC controller can only write to adc one bit at a time at rising clock edge
        """
        self.logger.debug("WRITING ADDR: %s VAL: %s" % (hex(addr), hex(data)))

        SCLK = 0x200
        CS = self.chip_select
        IDLE = SCLK
        SDA_SHIFT = 8
        self._write(IDLE, word_offset=0)
        for i in range(8):
            addr_bit = (addr >> (8 - i - 1)) & 1
            state = (addr_bit << SDA_SHIFT) | CS
            self._write(state, word_offset=0)
            #self.logger.debug("Printing address state written to adc16_controller, word_offset=0, clock low")
            #self.logger.debug(np.binary_repr(state, width=32))
            state = (addr_bit << SDA_SHIFT) | CS | SCLK
            self._write(state, word_offset=0)
            #self.logger.debug("Printing address state written to adc16_controller, word_offset=0, clock high")
            #self.logger.debug(np.binary_repr(state, width=32))

        for j in range(16):
            data_bit = (data >> (16 - j - 1)) & 1
            state = (data_bit << SDA_SHIFT) | CS
            self._write(state, word_offset=0, blindwrite=True)
            #self.logger.debug("Printing data state written to adc16_controller, word_offset=0, clock low")
            #self.logger.debug(np.binary_repr(state, width=32))
            state = (data_bit << SDA_SHIFT) | CS | SCLK
            self._write(state, word_offset=0, blindwrite=True)
            #self.logger.debug("Printing data address state written to adc16_controller, word_offset=0, clock high")
            #self.logger.debug(np.binary_repr(state, width=32))

        self._write(IDLE, word_offset=0, blindwrite=True)

    def power_cycle(self):
        """ Power cycle the ADC """
        logging.info('Power cycling the ADC')
        self.power_off()
        self.power_on()

    def power_off(self):
        """ Turn power to ADC off """
        self.logger.info('Power ADC down')
        self.write_register('pd', 1)

    def power_on(self):
        """ Turn power to ADC on """
        self.logger.info('Power ADC up')
        self.write_register('pd', 0)

    def reset(self):
        """ Reset the ADC """

        # reset adc
        self.write_register('rst', 1)

    def initialize(self, chips='all', demux_mode=1, gain=1):
        """ Initialize the ADC

        Args:
            chip_select (str or list): 'all' or list of chips (a,b and/or c ) to enable. Defaults to 'all'
            demux_mode (int): Set demulitplexing to 1 (no interleave), 2 or 4 (interleave all). Defaults to 1.
            gain (int): Digital gain to apply, 1-32, default 1, below 8 recommended.
        """
        self.logger.info('Initializing ADC')
        self.set_chip_select(chips)

        self.reset()
        self.set_demux(demux_mode)
        self.set_gain(gain)
        self.power_cycle()


    def set_demux(self, demux_mode):
        """ Set demux factor for ADC mode

        Interleave all inputs: demux=4
        No interleaving: demux=1
        Interleaving ADC0 and ADC2: demux=2

        Args:
            demux_mode (int): Set demulitplexing to 1 (no interleave), 2 or 4 (interleave all)

        """
        self.demux_mode = demux_mode
        if self.demux_mode == 1:
            self.logger.info('Routing all four inputs to corresponding ADC channels')
            self.write_register('channel_num', 4)
            self.set_input1(1, 2, 3, 4)

        elif self.demux_mode == 2:
            self.logger.info('Setting ADC to interleave inputs 1 (ADC0) and 3 (ADC2)')
            self.write_register('channel_num', 2)
            self.set_input2(1, 3)

        elif self.demux_mode == 4:
            self.logger.info('Setting ADC to interleave input (ADC0)')
            self.write_register('channel_num', 1)
            self.set_input4(1)

        else:
            self.logger.error('demux_mode variable not assigned. Weird.')
            raise RuntimeError('Demux mode variable not assigned. Weird.')

    def set_input4(self, input_id):
        """ Set input for demux mode 4 """
        ip = self.INPUT_MAP[input_id]
        self.write_shared_registers({'inp_sel_adc1': ip,
                                     'inp_sel_adc2': ip})
        self.write_shared_registers({'inp_sel_adc3': ip,
                                     'inp_sel_adc4': ip})

    def set_input2(self, input_id1, input_id2):
        """ Set input for demux mode 2 """
        ip1 = self.INPUT_MAP[input_id1]
        ip2 = self.INPUT_MAP[input_id2]
        self.write_shared_registers({'inp_sel_adc1': ip1,
                                     'inp_sel_adc2': ip1})
        self.write_shared_registers({'inp_sel_adc3': ip2,
                                     'inp_sel_adc4': ip2})

    def set_input1(self, input_id1, input_id2, input_id3, input_id4):
        """ Set input for demux mode 1 """
        ip1 = self.INPUT_MAP[input_id1]
        ip2 = self.INPUT_MAP[input_id2]
        ip3 = self.INPUT_MAP[input_id3]
        ip4 = self.INPUT_MAP[input_id4]

        self.write_shared_registers({'inp_sel_adc1': ip1,
                                     'inp_sel_adc2': ip2})
        self.write_shared_registers({'inp_sel_adc3': ip3,
                                     'inp_sel_adc4': ip4})

    def set_inputs(self, *args):
        """ Set input routing for ADC chips

        Args: integer ids (1,2,3,4) for ADC mapping

        Notes:
            Wrapper for set_input1/2/4 functions.
            Example: set_adc_inputs(3,2,1,4)
        """
        if len(args) == 1:
            #self.set_demux(4)
            self.set_input4(args[0])
        elif len(args) == 2:
            #self.set_demux(2)
            self.set_input2(args[0], args[1])
        elif len(args) == 4:
            #self.set_demux(1)
            self.set_input1(args[0], args[1], args[2], args[3])
        else:
            raise RuntimeError("Num. inputs (%i) must be 1, 2, or 4." % (len(args)))

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

                            --------------
         0x25 ADDR          | D6  D5  D4 |
        ----------------------------------
        | en_ramp           |  X   0   0 |
        | dual_custom_pat   |  0   X   0 |
        | single_custom_pat |  0   0   X |
        ----------------------------------

                            ----------
        0x45 ADDR           | D0  D1 |
        ------------------------------
        | pat_deskew        | 0   X  |
        | pat_sync          | X   0  |
        ------------------------------
        """
        self.write_register('en_ramp',    0b000)
        self.write_register('pat_deskew', 0b000)
        if pattern == 'ramp':
            self.write_register('en_ramp', 0b100)
        elif pattern == 'deskew':
            self.write_register('pat_deskew', 0b01)
        elif pattern == 'sync':
            self.write_register('pat_sync', 0b10)
        else:
            self.logger.error('Invalid test pattern selected')
            raise RuntimeError('Invalid test pattern selected')
        time.sleep(1)

    def clear_pattern(self):
        """ Clears test pattern from ADCs """
        self.write_register('en_ramp',   0b000)
        self.write_register('pat_deskew', 0b00)

    def read_ram(self, device):
        SNAP_REQ = 0x00010000
        self._write(0, word_offset=1, blindwrite=True)
        self._write(SNAP_REQ, word_offset=1, blindwrite=True)
        # Read the device that is passed to the read_ram method,1024 elements at a time,
        # snapshot is a binary string that needs to get unpacked
        # Part of the read request is the size parameter,1024, which specifies the
        # amount of bytes to read form the device
        snapshot = self.host.read(device, 1024, offset=0)

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
        #		print('Bitslip state written to word_offset=1:',bin(state))
        self._write(0, word_offset=1, blindwrite=True)
        self._write(state, word_offset=1, blindwrite=True)
        self._write(0, word_offset=1, blindwrite=True)

    def delay_tap(self, tap, channel, chip_num):

        delay_tap_mask = 0x1f

        CHAN_SEL_MAP = {'1': 0x1 << (chip_num * 4),
                        '2': 0x2 << (chip_num * 4),
                        '3': 0x4 << (chip_num * 4),
                        '4': 0x8 << (chip_num * 4)}

        LANE_SEL_MAP = {'a': 2,
                        'b': 3}

        if channel == 'all':
            chan_select = (0xf << (chip_num * 4))
            self._write(0, word_offset=2, blindwrite=True)
            self._write(0, word_offset=3, blindwrite=True)
            # Set tap bits
            self._write(delay_tap_mask & tap, word_offset=1, blindwrite=True)
            # Set strobe bits
            self._write(chan_select, word_offset=2, blindwrite=True)
            self._write(chan_select, word_offset=3, blindwrite=True)
            # Clear all bits
            for wo in (1, 2, 3):
                self._write(0, word_offset=wo, blindwrite=True)
            # Note this return statement, after all channels have been bitslip it'll exit out of the function.
            # the function is called again after figuring out the best tap with a single channel argument.
            return

        else:
            # Channel should be of form '1a' or '2b' etc
            chan_select = CHAN_SEL_MAP[channel[0]]
            lane_offset = LANE_SEL_MAP[channel[1]]

        self._write(0, word_offset=lane_offset, blindwrite=True)
        # Set tap bits
        self._write(delay_tap_mask & tap, word_offset=1, blindwrite=True)
        # Set strobe bits
        self._write(chan_select, word_offset=lane_offset, blindwrite=True)
        # Clear all bits
        for wo in (1, 2, 3):
            self._write(0, word_offset=wo, blindwrite=True)


    def test_tap(self, chip_num, taps):
        """
        returns an array of error counts for a given tap(assume structure chan 1a,
        chan 1b, chan 2a, chan 2b etc.. until chan 4b
        taps argument can have a value of an int or a string. If it's a string then it will
        iterate through all 32 taps
        if it's an int it will only delay all channels by that particular tap value.
        """
        # Form dicts for counting channel erros and offsets
        chan_ids     = ['1a', '1b', '2a', '2b', '3a', '3b', '4a', '4b']
        chan_offsets = dict(zip(chan_ids, range(8)))
        zeros        = [0, 0, 0, 0, 0, 0, 0, 0]
        error_count  = []
        error_count_all = []

        if taps == 'all':
            # read_ram returns an array of data form a snapshot from ADC output
            for tap in range(32):
                error_count_all.append(self.test_tap(chip_num, tap))
            return error_count_all
        else:
            chan_errs = dict(zip(chan_ids, zeros))
            # read_ram reuturns an array of data form a sanpshot from ADC output
            self.delay_tap(taps, 'all', chip_num)
            data = self.read_ram('adc16_wb_ram{0}'.format(chip_num))
            # each tap will return an error count for each channel and lane,
            # so an array of 8 elements with an error count for each
            self.logger.debug("TAPS %s | %s" % (taps, data))
            for i in range(0, 1024, 8):
                for chan_id, chan_offset in chan_offsets.items():
                    if data[i + chan_offset] != 0x2a:
                        chan_errs[chan_id] += 1

            error_count.append(
                [chan_errs['1a'], chan_errs['1b'], chan_errs['2a'], chan_errs['2b'],
                 chan_errs['3a'], chan_errs['3b'], chan_errs['4a'], chan_errs['4b']]
                )
            self.logger.debug('Chip {0} Error count for {1} tap: {2}'.format(chip_num, taps, error_count))
            return (error_count)


    def walk_taps(self):
        # Set FPGA to demux 4 because it makes snap blocks easier to interpret
        self.host.fpga_set_demux(4)

        for chip, chip_num in sorted(self.chips.items()):
            self.logger.info('Calibrating chip %s...' % chip)
            self.logger.debug('Setting deskew pattern...')
            self.enable_pattern('deskew')
            self.logger.debug('Stuff in chip after enabling test mode\n')
            self.logger.debug(self.read_ram('adc16_wb_ram{0}'.format(chip_num)))
            self.logger.debug('Taps before bitslipping anything\n')
            self.logger.debug(self.test_tap(chip_num, 'all'))

            # check if either of the extreme tap setting returns zero errors in any one of the channels.
            # Bitslip if True. This is to make sure that the eye of the pattern is swept completely
            error_counts_0  = self.test_tap(chip_num, 0)
            error_counts_31 = self.test_tap(chip_num, 31)
            for i in range(8):
                if not (error_counts_0[0][i]) or not (error_counts_31[0][i]):
                    self.logger.debug('Bitslipping chan %i' % i)
                    self.bitslip(chip_num, i)
                    error_counts_0  = self.test_tap(chip_num, 0)
                    error_counts_31 = self.test_tap(chip_num, 31)

            # error_list is a list of 32 'rows'(corresponding to the 32 taps) , each row containing
            # 8 elements,each element is the number of errors
            # of that lane  when compared to the expected value. read_ram method unpacks 1024 bytes. There are 8
            # lanes so each lane gets 1024/8=128 read outs from a single call to read_ram method,
            # like this, channel_1a etc. represent the errors in that channel
            # tap 0: [ channel_1a channel_1b channel_2a channel_2b channel_3a channel_3b channel_4a channel_4b]
            # tap 1: [ channel_1a channel_1b channel_2a channel_2b channel_3a channel_3b channel_4a channel_4b]
            # .....: [ channel_1a channel_1b channel_2a channel_2b channel_3a channel_3b channel_4a channel_4b]
            # tap 31:[ channel_1a channel_1b channel_2a channel_2b channel_3a channel_3b channel_4a channel_4b]
            error_list = self.test_tap(chip_num, 'all')
            good_tap_range = []
            best_tap_range = []
            self.logger.debug('Printing the list of errors, each row is a tap\n')
            self.logger.debug(['chan1a', 'chan1b', 'chan2a', 'chan2b', 'chan3a', 'chan3b', 'chan4a', 'chan4b'])
            self.logger.debug(np.array(error_list))

            # This loop goes through error_list, finds the elements with a value of 0 and appends them
            # to the good tap range list
            # It also picks out the elements corresponding to different channels and groups them together.
            # The error_list is a list where each 'row' is a different tap
            # I wanted to find the elements in each channel that have zero errors,
            # group the individual channels, and get the value of the tap in which they're in
            # - which is the index of the row
            for i in range(8):
                good_tap_range.append([])
                # j represents the tap value
                for j in range(32):
                    # i represents the channel/lane value
                    if error_list[j][i] == 0:
                        good_tap_range[i].append(j)
                        #	find the min and max of each element of good tap range and call delay tap
            self.logger.debug('Printing good tap values for each channel - each row is a different channel')

            for i in range(len(good_tap_range)):
                logging.debug('Channel {0}: {1}'.format(i + 1, good_tap_range[i]))

            channels = ['1a', '1b', '2a', '2b', '3a', '3b', '4a', '4b']
            for k in range(8):
                min_tap = min(good_tap_range[k])
                max_tap = max(good_tap_range[k])

                best_tap = (min_tap + max_tap) // 2
                self.delay_tap(best_tap, channels[k], chip_num)
            self.logger.debug('Printing the calibrated data from ram{0}.....'.format(self.chips[chip]))
            self.logger.debug(self.read_ram('adc16_wb_ram{0}'.format(self.chips[chip])))

            # Bitslip channels until the sync pattern is captured
            self.sync_chips(chip_num)

        # Set FPGA back to acutal demux mode
        self.host.fpga_set_demux(self.demux_mode)

    def sync_chips(self, chip_num):
        """ Synchronize chips with bitslip """
        self.enable_pattern('sync')

        snap = self.read_ram('adc16_wb_ram{0}'.format(chip_num))
        self.logger.debug('Snapshot before bitslipping:\n')
        self.logger.debug(snap[0:8])

        for i in range(8):
            loop_ctl = 0
            while snap[i] != 0x70:
                self.logger.debug('Bitslipping channel %i\n' % i)
                self.bitslip(chip_num, i)
                snap = self.read_ram('adc16_wb_ram{0}'.format(chip_num))
                self.logger.debug('Snapshot after bitslipping:\n')
                self.logger.debug(snap[0:8])
                loop_ctl += 1
                if loop_ctl > 10:
                    err = "Bitslipping is not working. Are you using the latest Jasper libraries?"
                    self.logger.error(err)
                    raise RuntimeError(err)

    def clock_locked(self):
        """ Check if CLK is locked """
        locked_bit = self.host.read_int(self.control_register, word_offset=0) >> 24
        if locked_bit & 3:
            self.logger.info('ADC clock is locked.')
            self.logger.info('Board clock: %2.4f MHz' % self.host.est_brd_clk())
            return True
        else:
            self.logger.info('ADC clock not locked. Check clock and/or demux mode.')
            return False

    def check_rms(self):
        """ Calculate RMS of ADC snapshot and print to screen """
        for chip_id in (0,1,2):
            snapshot = self.read_ram('adc16_wb_ram{0}'.format(chip_id))
            rms = np.std(snapshot)
            print("%06s ADC %i: %2.2f" % (self.host.host, chip_id, rms))

    def set_gain(self, gain):
        """ Set gain value on ADCs"""
        self.gain = gain
        if self.demux_mode == 1:
            self.write_shared_registers({'cgain4_ch1': gain,
                                         'cgain4_ch2': gain,
                                         'cgain4_ch3': gain,
                                         'cgain4_ch4': gain})
        elif self.demux_mode == 2:
            self.write_shared_registers({'cgain2_ch1': gain,
                                         'cgain2_ch2': gain})
        elif self.demux_mode == 4:
            self.write_register('cgain1_ch1', gain)
        else:
            err = "Demux Mode is not set"
            self.logger.error(err)
            raise RuntimeError(err)

    def calibrate(self):
        """" Run SERDES calibration routines """
        if self.clock_locked():
            # Calibrate ADC by going through various tap values
            self.walk_taps()
            # Clear pattern setting registers so real data could be taken
            self.clear_pattern()
        else:
            err = 'Could not calibrate, ADC clock not locked.'
            self.logger.error(err)
            raise RuntimeError(err)


