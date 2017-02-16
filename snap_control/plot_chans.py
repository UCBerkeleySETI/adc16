import matplotlib.pyplot as plt
import logging

import snap

def cmd_tool(args=None):
    from argparse import ArgumentParser

    p = ArgumentParser(description='python plot_chans.py HOST')
    p.add_argument('host', type=str, default='', help='specify the host name')
    p.add_argument('-p', '--port', dest='katcp_port', type=int, default=7147,
                   help='KATCP port to connect to (default 7147)')
    p.add_argument('-d', '--demux', dest='demux_mode', type=int, default=1,
                   help='ADC demux mode (1, 2 or 4)')

    args = p.parse_args()

    # define an ADC16 class object and pass it keyword arguments
    s = snap.SnapBoard(args.host, args.katcp_port)

    chip_dict = {
        'a': 0,
        'b': 1,
        'c': 2
    }
    s.adc.set_chip_select(('a', 'b', 'c'))

    plt.figure('plot_chans', figsize=(8, 6))

    for chip, chip_num in chip_dict.iteritems():

        # calibrate the snap_control chips using test patterns
        # s.adc.set_demux_fpga(1)
        snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_num))
        #    for i in snapshot:
        #        print i
        snapshot = snapshot.tolist()
        input1_data = []
        input2_data = []
        input3_data = []
        input4_data = []
        i = 0

        if args.demux_mode == 2:
            s.enable_pattern('deskew')
            snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_num))
            plt.subplot(3, 3, 1 + chip_num)
            plt.title('Test Pattern chip %s' % chip)
            plt.ylim([0, 50])
            plt.plot(snapshot)
            s.adc.write(0x25, 0x00)
            s.adc.write(0x45, 0x00)
            snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_num))
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

        elif args.demux_mode == 1:
            s.adc.enable_pattern('deskew')
            snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_num))
            plt.subplot(5, 3, 1 + chip_num)
            plt.ylim([0, 50])
            plt.title('Test Pattern chip %s' % chip)
            plt.plot(snapshot)
            s.adc.write(0x25, 0x00)
            s.adc.write(0x45, 0x00)
            snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_num))
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

        elif args.demux_mode == 4:
            s.adc.enable_pattern('deskew')
            snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_num))
            plt.subplot(2, 3, 1 + chip_num)
            plt.ylim([0, 50])
            plt.title('Test Pattern chip %s' % chip)
            plt.plot(snapshot)
            s.adc.write(0x25, 0x00)
            s.adc.write(0x45, 0x00)
            snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_num))
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
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    cmd_tool()