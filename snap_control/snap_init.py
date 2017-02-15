import snap

def cmd_tool(args=None):
    from argparse import ArgumentParser
    p = ArgumentParser(description='python snap_init.py HOST BOF_FILE [OPTIONS]')
    p.add_argument('host', type=str, default='', help='specify the host name')
    p.add_argument('bof', type=str, default='', help='specify the bof file to load unto FPGA')
    p.add_argument('-d', '--demux', dest='demux_mode', type=int, default=2,
                   help='Set demux mode 1/2/4')  # add the explanation of different demux modes
    p.add_argument('-g', '--gain', dest='gain', type=int, default=1,
                   help='Possible gain values (choose one): { 1 1.25 2 2.5 4 5 8 10 12.5 16 20 25 32 50 }, default is 1')
    p.add_argument('-i', '--iters', dest='num_iters', type=int, default=1,
                   help='Enter the number of snaps per tap')
    p.add_argument('-k', '--katcp_port', dest='katcp_port', type=int, default=7147,
                   help='KATCP port to use (default 7147)')
    p.add_argument('-r', '--reg', nargs='+', dest='registers', type=int, default=[],
                   help='enter registers and their values in [REGISTER] [VALUE] format')
    p.add_argument('-c', '--chips', nargs='+', dest='chips', type=str, default=['a', 'b', 'c'],
                   help='Input chips you wish to calibrate. Ex: -c a b . Default all chips:  a b c.')
    p.add_argument('-s', '--skip', action='store_true', dest='skip_flag',
                   help='specify this flag if you want to skip programming the bof file unto the FPGA')
    p.add_argument('-v', '--verbosity', action='store_true', dest='verbosity',
                   help='increase output verbosity')  # add the explanation of different demux modes
    p.add_argument('-p', '--pattern', dest='test_pattern', type=str, default='deskew',
                   help='input the test pattern to calibrate adc(ex. deskew:10101010, sync:11110000), \
                               for custom pattern just enter bitstream(ex.-p 10110110 or -p 0 etc.')

    args = p.parse_args()

    # define an ADC16 class object and pass it keyword arguments
    s = snap.SnapBoard(args.host, args.katcp_port, timeout=10)
    
    s.program(boffile=args.bof, 
              chips=args.chips, 
              demux_mode=args.demux_mode, 
              gain=args.gain)


if __name__ == "__main__":
    cmd_tool()
