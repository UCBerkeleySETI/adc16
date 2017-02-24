"""
# plot_chans.py

Plotting scripts for SnapBoard

"""
import snap
import os
import numpy as np

try:
    import seaborn as sns
    sns.set_style('white')
except:
    pass

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
    p.add_argument('-r', '--remote', dest='remote_connection', action='store_true', default=False,
                   help='Faster plotting for remote connection')
    p.add_argument('-f', '--fft', dest='do_fft', action='store_true', default=False,
                   help='Plot ADC channel bandpass (i.e. take FFT^2 of snapshot data)')                   
    p.add_argument('-T', '--deskewpattern', dest='pattern_deskew', action='store_true', default=False,
                   help='Plot test pattern (deskew). Value should be a constant 42.')
    #p.add_argument('-T', '--syncpattern', dest='pattern_sync', action='store_true', default=False,
    #               help='Plot test pattern (sync)')
    p.add_argument('-R', '--ramppattern', dest='pattern_ramp', action='store_true', default=False,
                   help='Plot test pattern (ramp)')                   

    args = p.parse_args()

    if args.remote_connection:
        import matplotlib
        # see http://matplotlib.org/faq/usage_faq.html#what-is-a-backend
        matplotlib.use('Agg')

    import matplotlib.pyplot as plt

    # define an ADC16 class object and pass it keyword arguments
    s = snap.SnapBoard(args.host, args.katcp_port)
    
    if args.pattern_deskew:
        s.adc.enable_pattern('deskew')
    #if args.pattern_sync:
    #    s.adc.enable_pattern('sync')
    if args.pattern_ramp:
        s.adc.enable_pattern('ramp')

    plt.figure('plot_chans', figsize=(8, 6))
    
    for chip_id in (0,1,2):
        snapshot = s.adc.read_ram('adc16_wb_ram{0}'.format(chip_id))
        
        if args.demux_mode == 1:
            d1, d2, d3, d4 = demux_data(snapshot, args.demux_mode)
            if args.do_fft:
                d1 = np.fft.rfft(d1)
                d2 = np.fft.rfft(d2)
                d3 = np.fft.rfft(d3)
                d4 = np.fft.rfft(d4)
            plt.subplot(3, 4, 1 + 4*chip_id)
            plt.plot(d1, c='#cc00cc')
            plt.title('Input 1 data chip %s' % chip_id)
            plt.subplot(3, 4, 2 + 4*chip_id)
            plt.plot(d2, c='#00cccc')
            plt.title('Input 2 data chip %s' % chip_id)
            plt.subplot(3, 4, 3 + 4*chip_id)
            plt.plot(d3, c='#cccc00')
            plt.title('Input 3 data chip %s' % chip_id)
            plt.subplot(3, 4, 4 + 4*chip_id)
            plt.plot(d4, c='#cc0000')
            plt.title('Input 4 data chip %s' % chip_id)
        
        elif args.demux_mode == 2:
            d1, d3 = demux_data(snapshot, args.demux_mode)
            if args.do_fft:
                d1 = np.fft.rfft(d1)
                d3 = np.fft.rfft(d3)
            plt.subplot(3, 2, 1 + 2*chip_id)
            plt.plot(d1)
            plt.title('Input 1 data chip %s' % chip_id)
            plt.subplot(3, 2, 2 + 2*chip_id)
            plt.plot(d3)
            plt.title('Input 3 data chip %s' % chip_id)
        
        elif args.demux_mode == 4:
            d1 = demux_data(snapshot, args.demux_mode)
            if args.do_fft:
                d1 = np.fft.rfft(d1)
            plt.subplot(3, 1, 1 + chip_id)
            plt.plot(d1)
            plt.title('Input 1 data chip %s' % chip_id)
        else:
            print('Improper demux mode selected, possible values are 1, 2 and 4')
            exit(1)
    
    # Remember to turn off test pattern
    s.adc.clear_pattern()
        
    plt.tight_layout()
    if args.remote_connection:
        plt.savefig('plot.png')
        os.system('feh plot.png')
    else:
        plt.show()

if __name__ == '__main__':
    cmd_tool()