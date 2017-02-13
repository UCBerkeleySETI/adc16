import snap
import matplotlib.pyplot as plt
import logging

if __name__ == '__main__':
    from argparse import ArgumentParser

    p = ArgumentParser(description='python snap_init.py HOST BOF_FILE [OPTIONS]')
    p.add_argument('host', type=str, default='', help='specify the host name')
    p.add_argument('bof', type=str, default='', help='specify the bof file to load unto FPGA')
    p.add_argument('-d', '--demux', dest='demux_mode', type=int, default=2,
                   help='Set demux mode 1/2/4')  # add the explanation of different demux modes
    p.add_argument('-g', '--gain', dest='gain', type=int, default=0, help='Set the gain')
    p.add_argument('-i', '--iters', dest='num_iters', type=int, default=1, help='Enter the number of snaps per tap')
    p.add_argument('-r', '--reg', nargs='+', dest='registers', type=int, default=[],
                   help='enter registers and their values in [REGISTER] [VALUE] format')
    p.add_argument('-c', '--chips', nargs='+', dest='chips', type=str, default=['a', 'b', 'c'],
                   help='Input chips you wish to calibrate. Ex: -c a b . Default all chips:  a b c.')
    p.add_argument('-s', '--skip', action='store_true', dest='skip_flag',
                   help='specify this flag if you want to skip programming the bof file unto the FPGA')
    p.add_argument('-v', '--verbosity', action='store_true', dest='verbosity',
                   help='increase output verbosity')  # add the explanation of different demux modes
    p.add_argument('-p', '--pattern', dest='test_pattern', type=str, default='deskew',
                   help='input the test pattern to calibrate adc(ex. deskew:10101010, sync:11110000),for custom pattern just enter bitstream(ex.-p 10110110 or -p 0 etc.')

    args = p.parse_args()
    demux_mode = args.demux_mode
    gain = args.gain
    num_iters = args.num_iters
    registers = args.registers
    bof = args.bof
    host = args.host
    skip_flag = args.skip_flag
    verbosity = args.verbosity
    chips = args.chips
    test_pattern = args.test_pattern

    # define an ADC16 class object and pass it keyword arguments
    a = snap.ADC16(**{'host': host, 'bof': bof, 'skip_flag': skip_flag, 'verbosity': verbosity, 'chips': chips,
                      'demux_mode': demux_mode, 'test_pattern': test_pattern, 'gain': gain})

    chip_dict = {}
    for chip in chips:
        if chip == 'a' or chip == 'A':
            chip_dict['a'] = 0
        elif chip == 'b' or chip == 'B':
            chip_dict['b'] = 1
        elif chip == 'c' or chip == 'C':
            chip_dict['c'] = 2
        else:
            logging.error('Invalid chip name passed, available values: a, b or c, default is all chips selected')
            exit(1)

    for chip, chip_num in chip_dict.iteritems():

        # calibrate the snap_board chips using test patterns
        # a.set_demux_fpga(1)
        snapshot = a.read_ram('adc16_wb_ram{0}'.format(chip_num))
        #    for i in snapshot:
        #        print i
        snapshot = snapshot.tolist()
        input1_data = []
        input2_data = []
        input3_data = []
        input4_data = []
        i = 0
        if demux_mode == 2:
            a.enable_pattern('deskew')
            snapshot = a.read_ram('adc16_wb_ram{0}'.format(chip_num))
            plt.subplot(3, 3, 1 + chip_num)
            plt.title('Test Pattern chip %s' % chip)
            plt.ylim([0, 50])
            plt.plot(snapshot)
            a.write_adc(0x25, 0x00)
            a.write_adc(0x45, 0x00)
            snapshot = a.read_ram('adc16_wb_ram{0}'.format(chip_num))
            while i < 1024:
                input1_data.append(snapshot[i])
                input1_data.append(snapshot[i + 4])
                input1_data.append(snapshot[i + 1])
                input1_data.append(snapshot[i + 5])

                input3_data.append(snapshot[i + 2])
                input3_data.append(snapshot[i + 6])
                input3_data.append(snapshot[i + 3])
                input3_data.append(snapshot[i + 7])
                i += 8
            plt.subplot(3, 3, 4 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(input1_data)
            plt.title('Input 1 data chip %s' % chip)
            plt.subplot(3, 3, 7 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(input3_data)
            plt.title('Input 3 data chip %s' % chip)

        elif demux_mode == 1:
            a.enable_pattern('deskew')
            snapshot = a.read_ram('adc16_wb_ram{0}'.format(chip_num))
            plt.subplot(5, 3, 1 + chip_num)
            plt.ylim([0, 50])
            plt.title('Test Pattern chip %s' % chip)
            plt.plot(snapshot)
            a.write_adc(0x25, 0x00)
            a.write_adc(0x45, 0x00)
            snapshot = a.read_ram('adc16_wb_ram{0}'.format(chip_num))
            while i < 1024:
                input1_data.append(snapshot[i])
                input2_data.append(snapshot[i + 1])
                input3_data.append(snapshot[i + 2])
                input4_data.append(snapshot[i + 3])

                i += 4
            plt.subplot(5, 3, 4 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(input1_data)
            plt.title('Input 1 data')
            plt.subplot(5, 3, 7 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(input2_data)
            plt.title('Input 2 data')
            plt.subplot(5, 3, 10 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(input3_data)
            plt.title('Input 3 data')
            plt.subplot(5, 3, 13 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(input4_data)
            plt.title('Input 4 data')
        elif demux_mode == 4:
            a.enable_pattern('deskew')
            snapshot = a.read_ram('adc16_wb_ram{0}'.format(chip_num))
            plt.subplot(2, 3, 1 + chip_num)
            plt.ylim([0, 50])
            plt.title('Test Pattern chip %s' % chip)
            plt.plot(snapshot)
            a.write_adc(0x25, 0x00)
            a.write_adc(0x45, 0x00)
            snapshot = a.read_ram('adc16_wb_ram{0}'.format(chip_num))
            while i < 1024:
                input1_data.append(snapshot[i])
                input1_data.append(snapshot[i + 2])
                input1_data.append(snapshot[i + 4])
                input1_data.append(snapshot[i + 6])
                input1_data.append(snapshot[i + 1])
                input1_data.append(snapshot[i + 3])
                input1_data.append(snapshot[i + 5])
                input1_data.append(snapshot[i + 7])
                i += 8
            plt.subplot(2, 3, 4 + chip_num)
            plt.ylim([-6, 6])
            plt.plot(input1_data)
            plt.title('Input 1 data chip %s' % chip)
        else:
            print('Improper demux mode selected, possible values are 1, 2 and 4')
            exit(1)
    plt.ylim([-6, 6])
    plt.show()
