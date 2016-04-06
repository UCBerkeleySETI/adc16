#import adc16 ##once the 
import adc16


if __name__ == '__main__':
	from argparse import ArgumentParser
	p = ArgumentParser(description='python adc16_init.py [OPTIONS]')
	p.add_argument('-b','--bof', dest='bof', type=str,default='',help='specify the bof file to load unto FPGA')
	p.add_argument('-host','--host',dest='host', type=str, default='',help='specify the host name')
	p.add_argument('-d', '--demux', dest='demux_mode', type=int,default=1,help='Set demux mode 1/2/4') #add the explanation of different demux modes
	p.add_argument('-g', '--gain', dest='gain', type=int,default=0,help='Set the gain')
	p.add_argument('-i','--iters', dest='num_iters', type=int,default=1,help='Enter the number of snaps per tap')
	p.add_argument('-r', '--reg', nargs='+', dest='registers', type=int,default=[],help='enter registers and their values in [REGISTER] [VALUE] format')
	p.add_argument('-s', action = 'store_true', dest = 'skip_flag', help='specify this flag if you want to skip programming the bof file unto the FPGA')	
	
	args = p.parse_args()
	demux_mode=args.demux_mode
	gain = args.gain
	num_iters = args.num_iters
	registers = args.registers
	bof = args.bof
	host = args.host
	skip_flag = args.skip_flag
	
print("Connecting to %s" % host)

a=adc16.ADC16(**{'host':host, 'bof':bof, 'skip_flag':skip_flag})

#Reset and a powerdown cycle as specified in the HMCAD1511 documentation
a.reset()
a.power_down()
a.power_up()
#a.adc16_based()

#enabling pattern:
#a.write_adc(0x25,0x0040)
#print(a.read_int('adc16_wb_ram0'))

a.enable_pattern('ramp')

a.read_ram('adc16_wb_ram0')

#a.list_reg()
#a.write_reg()
#a.read_reg()

	
	
