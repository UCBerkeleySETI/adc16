import matplotlib.pyplot as plt
import logging

import snap


def demux_data(snapshot, demux):
    """ Demux and interleaves data for plotting """
    input1_data = []
    input2_data = []
    input3_data = []
    input4_data = []

    if demux == 1:
        for i in range(0, 1024, 4):
            input1_data.append(snapshot[i + 0])
            input2_data.append(snapshot[i + 1])
            input3_data.append(snapshot[i + 2])
            input4_data.append(snapshot[i + 3])
            return input1_data, input2_data, input3_data, input4_data

    elif demux == 2:
        for i in range(0, 1024, 8):
            input1_data.append(snapshot[i + 0])
            input1_data.append(snapshot[i + 4])
            input1_data.append(snapshot[i + 1])
            input1_data.append(snapshot[i + 5])

            input3_data.append(snapshot[i + 2])
            input3_data.append(snapshot[i + 6])
            input3_data.append(snapshot[i + 3])
            input3_data.append(snapshot[i + 7])
            return input1_data, input3_data

    elif demux == 4:
        for i in range(0, 1024, 8):
            input1_data.append(snapshot[i + 0])
            input1_data.append(snapshot[i + 2])
            input1_data.append(snapshot[i + 4])
            input1_data.append(snapshot[i + 6])
            input1_data.append(snapshot[i + 1])
            input1_data.append(snapshot[i + 3])
            input1_data.append(snapshot[i + 5])
            input1_data.append(snapshot[i + 7])
            return input1_data

    else:
        raise RuntimeError("Weird demux factor, use 1, 2 or 4.")


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

        snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_num))

        if args.demux_mode == 1:
            d1, d2, d3, d4 = demux_data(snapshot, args.demux_mode)
            plt.subplot(4, 3, 1 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(d1, c='#cc00cc')
            plt.title('Input 1 data chip %s' % chip)
            plt.subplot(4, 3, 2 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(d2, c='#00cccc')
            plt.title('Input 2 data chip %s' % chip)
            plt.subplot(4, 3, 3 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(d3, c='#cccc00')
            plt.title('Input 3 data chip %s' % chip)
            plt.subplot(4, 3, 4 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(d4, c='#cc0000')
            plt.title('Input 4 data chip %s' % chip)

        elif args.demux_mode == 2:
            d1, d3 = demux_data(snapshot, args.demux_mode)
            plt.subplot(2, 3, 1 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(d1)
            plt.title('Input 1 data chip %s' % chip)
            plt.subplot(2, 3, 2 + chip_num)
            plt.ylim([-40, 40])
            plt.plot(d3)
            plt.title('Input 3 data chip %s' % chip)

        elif args.demux_mode == 4:
            d1 = demux_data(snapshot, args.demux_mode)
            plt.subplot(1, 3, 2 + chip_num)
            plt.ylim([-6, 6])
            plt.plot(d1)
            plt.title('Input 1 data chip %s' % chip)
        else:
            print('Improper demux mode selected, possible values are 1, 2 and 4')
            exit(1)
    plt.ylim([-6, 6])
    plt.tight_layout()
    plt.show()



if __name__ == '__main__':
    cmd_tool()