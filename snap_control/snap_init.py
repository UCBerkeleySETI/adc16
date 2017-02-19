import snap
import logging

def cmd_tool(args=None):
    from argparse import ArgumentParser
    p = ArgumentParser(description='python snap_init.py HOST BOF_FILE [OPTIONS]')
    p.add_argument('host', type=str, default='', help='specify the host name')
    p.add_argument('bof', type=str, default='', help='specify the bof file to load unto FPGA')
    p.add_argument('-d', '--demux', dest='demux_mode', type=int, default=2,
                   help='Set demux mode 1/2/4')  # add the explanation of different demux modes
    p.add_argument('-g', '--gain', dest='gain', type=int, default=1,
                   help='Possible gain values (choose one): { 1 1.25 2 2.5 4 5 8 10 12.5 16 20 25 32 50 }, default is 1')
    p.add_argument('-k', '--katcp_port', dest='katcp_port', type=int, default=7147,
                   help='KATCP port to use (default 7147)')
    p.add_argument('-c', '--chips', nargs='+', dest='chips', type=str, default='all',
                   help='Input chips you wish to calibrate. Default all chips:  a b c.')
    p.add_argument('-s', '--silent', action='store_true', default=False,
                   help='Silence all logging info.')
    p.add_argument('-v', '--verbose', action='store_true', default=False,
                   help='Verbose mode, for debugging.')
                   
    args = p.parse_args()

    # define an ADC16 class object and pass it keyword arguments
    s = snap.SnapBoard(args.host, args.katcp_port, timeout=10)
    
    if args.verbose:
        s.logger.setLevel(logging.DEBUG)
        s.adc.logger.setLevel(logging.DEBUG)
    
    if not args.silent:
        s.logger.setLevel(logging.INFO)
        s.adc.logger.setLevel(logging.INFO)
    
    if not args.silent:
        print("Programming %s with %s" % (args.host, args.bof))
    
    s.program(boffile=args.bof, 
              chips=args.chips, 
              demux_mode=args.demux_mode, 
              gain=args.gain)
    
    if not args.silent:
        print("DONE.")


if __name__ == "__main__":
    cmd_tool()
