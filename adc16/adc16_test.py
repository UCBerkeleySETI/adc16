import corr
import numpy as np
import time
import os
import sys
import struct
katcp_port=7147
class ADC16():#katcp.RoachClient):

	def __init__(self,**kwargs):
		#katcp_port to connect to with FpgaClient			
		self.katcp_port = 7147
		#Make a dictionary out of chips specified on command line. 
		#mapping chip letters to numbers to facilitate writing to adc16_controller
		self.chips = {}
		self.demux_mode = kwargs['demux_mode']
		for chip in kwargs['chips']:
			if chip == 'a':
				self.chips['a'] = 0
			elif chip == 'b':
				self.chips['b'] = 1
			elif chip == 'c':
				self.chips['c'] = 2

			elif chip == 'd':
				self.chips['d'] = 3
			elif chip == 'e':
				self.chips['e'] = 4
			elif chip == 'f':
				self.chips['f'] = 5
			elif chip == 'g':
				self.chips['g'] = 6
			elif chip == 'h':
				self.chips['h'] = 7

		if kwargs['verbosity'] == True:
			def verboseprint(*args):
				for arg in args:
					print('\n',arg)
		else:
			self.verboseprint = lambda *a: None 
		
		print('Connecting to SNAP.....')
		#Instantiating a snap object with attributes of FpgaClient class
		self.snap = corr.katcp_wrapper.FpgaClient(kwargs['host'], self.katcp_port, timeout=10)
		time.sleep(1)

		if  self.snap.is_connected():
			print('Connected to SNAP!')	

		#Dealing with flags passed into argsparse at the prompt by the user
		if kwargs['skip_flag'] == True:
			print('Not programming the bof file')
		else:
			print('Programming with bof file....')
			self.snap.progdev(kwargs['bof'])
			print('Programmed!')

	def write_adc(self,addr,data):
		SCLK = 0x200
		CS = 0xff
		IDLE = SCLK
		SDA_SHIFT = 8
#		addr = np.atleast_1d(addr)
#		data = np.atleast_1d(data)
		self.snap.write_int('adc16_controller',IDLE,offset=0,blindwrite=True)
		for i in range(8):
			addr_bit = (addr>>(8-i-1))&1
			state = (addr_bit<<SDA_SHIFT) | CS
			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
		#	print(np.binary_repr(state,width=32))
			state = (addr_bit<<SDA_SHIFT) | CS | SCLK
			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
		#	print(np.binary_repr(state,width=32))
		for j in range(16):
			data_bit = (data>>(16-j-1))&1
			state = (data_bit<<SDA_SHIFT) | CS
			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
		#	print(np.binary_repr(state,width=32))
			state =( data_bit<<SDA_SHIFT) | CS | SCLK	
			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)		
		#	print(np.binary_repr(state,width=32))
		
#		for j in range(16):
#			data_bit = (data>>(j))&1
#			state = (data_bit<<SDA_SHIFT) | CS
#			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
#			state =( data_bit<<SDA_SHIFT) | CS | SCLK	
#			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)		
#		for i in range(8):
#			addr_bit = (addr>>(i))&1
#			state = (addr_bit<<SDA_SHIFT) | CS
#			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
#			state = (addr_bit<<SDA_SHIFT) | CS | SCLK
#			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
		self.snap.write_int('adc16_controller',IDLE,offset=0,blindwrite=True)
		print(np.binary_repr(IDLE,width=32))

	def adc_init_seq(self):
#		self.snap.write_int('adc16_controller',0x100000,offset=1,blindwrite=True)
		#reset adc	
                self.write_adc(0x00,0x0001)
                #power adc down
		self.write_adc(0x0f,0x0200)	
                #power adc up
		self.write_adc(0x0f,0x0000)
	def enable_pattern(self,pattern):                                                                                           
		self.write_adc(0x25,0x00)
		self.write_adc(0x45,0x00)
                if pattern=='ramp':
                        self.write_adc(0x25,0x0040)
                elif pattern=='deskew':
                        self.write_adc(0x45,0x0001)
                elif pattern=='sync':
                        self.write_adc(0x45,0x0002)
		elif pattern=='custom':
			self.write_adc(0x26,0xff00)
                else:
                        print('Pattern specified not found, possible options: ramp, deskew and sync')
                        exit(1)

	def read_ram(self,device):
		SNAP_REQ = 0x00010000
		bin_data = []
		self.snap.write_int('adc16_controller',0, offset=1,blindwrite=True)
		self.snap.write_int('adc16_controller',SNAP_REQ, offset=1,blindwrite=True)
		snapshot = self.snap.read(device,1024,offset=0)
		
		string_data = struct.unpack('>1024b', snapshot)
		array_data = np.array(string_data)
		return array_data


if __name__ == '__main__':
	from argparse import ArgumentParser
	p = ArgumentParser(description = 'python adc16_init.py HOST BOF_FILE [OPTIONS]')
	p.add_argument('host', type = str, default = '', help = 'specify the host name')
	p.add_argument('bof', type = str, default = '', help = 'specify the bof file to load unto FPGA')
	p.add_argument('-d', '--demux', dest = 'demux_mode', type = int, default = 1, help = 'Set demux mode 1/2/4') #add the explanation of different demux modes
	p.add_argument('-g', '--gain', dest = 'gain', type = int, default = 0, help = 'Set the gain')
	p.add_argument('-i','--iters', dest = 'num_iters', type = int, default=1, help = 'Enter the number of snaps per tap')
	p.add_argument('-r', '--reg', nargs = '+', dest = 'registers', type = int, default = [], help = 'enter registers and their values in [REGISTER] [VALUE] format')
	p.add_argument('-c', '--chips', nargs = '+', dest = 'chips', type = list, default = ['a' 'b' 'c'], help = 'Input chips you wish to calibrate. Ex: -c a b c')
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
#	print(host, bof, verbosity, skip_flag)

	print("Connecting to %s" % host)
	#define an ADC16 class object and pass it keyword arguments
	a=ADC16(**{'host':host, 'bof':bof, 'skip_flag':skip_flag, 'verbosity':verbosity, 'chips':chips,'demux_mode':demux_mode})
	#a=adc16.ADC16(host=host, bof=bof,....)
	#a.adc_init_seq()
	#calibrate the adc16 chips using test patterns
	a.enable_pattern('custom')
	print('Values after setting the custom pattern of ones')
	data = a.read_ram('adc16_wb_ram0')
	data[data<0] += 128	
	for value in data:
		print(bin(value))
	a.enable_pattern('deskew')
	print('Values after setting the deskew pattern\n')
	a.read_ram('adc16_wb_ram0')	
	data = a.read_ram('adc16_wb_ram0')
	data[data<0] += 128	
	for value in data:
		print(bin(value))
