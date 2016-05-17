
import adc16


if __name__ == '__main__':
	from argparse import ArgumentParser
	p = ArgumentParser(description = 'python adc16_init.py HOST BOF_FILE [OPTIONS]')
	p.add_argument('host', type = str, default = '', help = 'specify the host name')
	p.add_argument('bof', type = str, default = '', help = 'specify the bof file to load unto FPGA')
	p.add_argument('-d', '--demux', dest = 'demux_mode', type = int, default = 2, help = 'Set demux mode 1/2/4') #add the explanation of different demux modes
	p.add_argument('-g', '--gain', dest = 'gain', type = int, default = 0, help = 'Set the gain')
	p.add_argument('-i','--iters', dest = 'num_iters', type = int, default=1, help = 'Enter the number of snaps per tap')
	p.add_argument('-r', '--reg', nargs = '+', dest = 'registers', type = int, default = [], help = 'enter registers and their values in [REGISTER] [VALUE] format')
	p.add_argument('-c', '--chips', nargs = '+', dest = 'chips', type = list, default = ['a','b','c'], help = 'Input chips you wish to calibrate. Ex: -c a b . Default all chips:  a b c.')
	p.add_argument('-s', '--skip', action = 'store_true', dest = 'skip_flag', help = 'specify this flag if you want to skip programming the bof file unto the FPGA')	
	p.add_argument('-v', '--verbosity', action = 'store_true', dest = 'verbosity', help = 'increase output verbosity') #add the explanation of different demux modes
	args = p.parse_args()
	demux_mode=args.demux_mode
	gain = args.gain
	num_iters = args.num_iters
	registers = args.registers
	bof = args.bof
	host = args.host
	skip_flag = args.skip_flag
	verbosity = args.verbosity
	chips = args.chips

#define an ADC16 class object and pass it keyword arguments
a=adc16.ADC16(**{'host':host, 'bof':bof, 'skip_flag':skip_flag, 'verbosity':verbosity, 'chips':chips,'demux_mode':demux_mode})



#calibrate the adc16 chips using test patterns
a.calibrate()

	
	
