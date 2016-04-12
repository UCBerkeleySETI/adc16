import time
import copy
import corr
import os
import sys
import numpy as np
import struct
#from corr import katcp_wrapper
katcp_port=7147


# Provides KATCP wrapper around ADC16 based CASPER design.  Includes many
# convenience functions for writing to the registers of the ADC chips,
# calibrating the SERDES blocks, and accessing status info about the ADC16
# design and clock status.  While most access will be done via the methods of
# this class, there may be occasion to access the ADC16 controller directly
# (via the #adc16_controller method, which returns a KATCP::Bram object).
#
# Here is the memory map for the underlying #adc16_controller device:
#
#   # ======================================= #
#   # ADC16 3-Wire Register (word 0)          #
#   # ======================================= #
#   # LL = Clock locked bits                  #
#   # NNNN = Number of ADC chips supported    #
#   # RR = ROACH2 revision expected/required  #
#   # C = SCLK                                #
#   # D = SDATA                               #
#   # 7 = CSNH (chip select H, active high)   #
#   # 6 = CSNG (chip select G, active high)   #
#   # 5 = CSNF (chip select F, active high)   #
#   # 4 = CSNE (chip select E, active high)   #
#   # 3 = CSND (chip select D, active high)   #
#   # 2 = CSNC (chip select C, active high)   #
#   # 1 = CSNB (chip select B, active high)   #
#   # 0 = CSNA (chip select A, active high)   #
#   # ======================================= #
#   # |<-- MSb                       LSb -->| #
#   # 0000_0000_0011_1111_1111_2222_2222_2233 #
#   # 0123_4567_8901_2345_6789_0123_4567_8901 #
#   # ---- --LL ---- ---- ---- ---- ---- ---- #
#   # ---- ---- NNNN ---- ---- ---- ---- ---- #
#   # ---- ---- ---- --RR ---- ---- ---- ---- #
#   # ---- ---- ---- ---- ---- --C- ---- ---- #
#   # ---- ---- ---- ---- ---- ---D ---- ---- #
#   # ---- ---- ---- ---- ---- ---- 7654 3210 #
#   # |<--- Status ---->| |<--- 3-Wire ---->| #
#   # ======================================= #
#   # NOTE: LL reflects the runtime lock      #
#   #       status of a line clock from each  #
#   #       ADC board.  A '1' bit means       #
#   #       locked (good!).  Bit 5 is always  #
#   #       used, but bit 6 is only used when #
#   #       NNNN is 4 (or less).              #
#   # ======================================= #
#   # NOTE: NNNN and RR are read-only values  #
#   #       that are set at compile time.     #
#   #       They do not indicate the state    #
#   #       of the actual hardware in use     #
#   #       at runtime.                       #
#   # ======================================= #
#
#   # ======================================= #
#   # ADC16 Control Register (word 1)         #
#   # ======================================= #
#   # W  = Deux write-enable                  #
#   # MM = Demux mode                         #
#   # R = ADC16 Reset                         #
#   # S = Snap Request                        #
#   # H = ISERDES Bit Slip Chip H             #
#   # G = ISERDES Bit Slip Chip G             #
#   # F = ISERDES Bit Slip Chip F             #
#   # E = ISERDES Bit Slip Chip E             #
#   # D = ISERDES Bit Slip Chip D             #
#   # C = ISERDES Bit Slip Chip C             #
#   # B = ISERDES Bit Slip Chip B             #
#   # A = ISERDES Bit Slip Chip A             #
#   # T = Delay Tap                           #
#   # ======================================= #
#   # |<-- MSb                       LSb -->| #
#   # 0000 0000 0011 1111 1111 2222 2222 2233 #
#   # 0123 4567 8901 2345 6789 0123 4567 8901 #
#   # ---- -WMM ---- ---- ---- ---- ---- ---- #
#   # ---- ---- ---R ---- ---- ---- ---- ---- #
#   # ---- ---- ---- ---S ---- ---- ---- ---- #
#   # ---- ---- ---- ---- HGFE DCBA ---- ---- #
#   # ---- ---- ---- ---- ---- ---- ---T TTTT #
#   # ======================================= #
#   # NOTE: W enables writing the MM bits.    #
#   #       Some of the other bits in this    #
#   #       register are one-hot.  Using      #
#   #       W ensures that the MM bits will   #
#   #       only be written to when desired.  #
#   #       00: demux by 1 (single channel)   #
#   # ======================================= #
#   # NOTE: MM selects the demux mode.        #
#   #       00: demux by 1 (single channel)   #
#   #       01: demux by 2 (dual channel)     #
#   #       10: demux by 4 (quad channel)     #
#   #       11: undefined                     #
#   #       ADC board.  A '1' bit means       #
#   #       locked (good!).  Bit 5 is always  #
#   #       used, but bit 6 is only used when #
#   #       NNNN is 4 (or less).              #
#   # ======================================= #
#
#   # =============================================== #
#   # ADC16 Delay A Strobe Register (word 2)          #
#   # =============================================== #
#   # D = Delay Strobe (rising edge active)           #
#   # =============================================== #
#   # |<-- MSb                              LSb -->|  #
#   # 0000  0000  0011  1111  1111  2222  2222  2233  #
#   # 0123  4567  8901  2345  6789  0123  4567  8901  #
#   # DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  #
#   # |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  #
#   # H4 H1 G4 G1 F4 F1 E4 E1 D4 D1 C4 C1 B4 B1 A4 A1 #
#   # =============================================== #
#
#   # =============================================== #
#   # ADC0 Delay B Strobe Register (word 3)           #
#   # =============================================== #
#   # D = Delay Strobe (rising edge active)           #
#   # =============================================== #
#   # |<-- MSb                              LSb -->|  #
#   # 0000  0000  0011  1111  1111  2222  2222  2233  #
#   # 0123  4567  8901  2345  6789  0123  4567  8901  #
#   # DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  DDDD  #
#   # |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  #
#   # H4 H1 G4 G1 F4 F1 E4 E1 D4 D1 C4 C1 B4 B1 A4 A1 #
#   # =============================================== #



class ADC16():#katcp.RoachClient):
#	DEVICE_TYPEMAP = {
#			'adc16_controller' : 'bram',
#			'adc16_wb_ram0' : 'bram',
#			'adc16_wb_ram1' : 'bram',
#			'adc16_wb_ram2' : 'bram',
#			}
#
#
#	def device_typemap(self):
#		self.device_typemap |= copy.deepcopy(DEVICE_TYPEMAP)

	def __init__(self,**kwargs):
		#print(kwargs['host'])	
		self.snap = corr.katcp_wrapper.FpgaClient(kwargs['host'],katcp_port,timeout=10)
		time.sleep(1)
		if  self.snap.is_connected():
			print('Connected to SNAP')	
		if kwargs['skip_flag'] == True:
			print('Not programming the bof file')
		else:
			print('Programming with bof file....')
			self.snap.progdev(kwargs['bof'])
			print('Programmed!')

	def write_adc(self,addr,data):
		SCLK = 0x200
		CS = 0x00000001
		IDLE = SCLK
		SDA_SHIFT = 8
		addr = np.atleast_1d(addr)
		data = np.atleast_1d(data)
		self.snap.write_int('adc16_controller',IDLE,offset=0,blindwrite=True)
		for i in range(addr.shape[0]):
			addr_bit = (addr>>i)&1
			state = (addr_bit<<SDA_SHIFT) | CS
			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
			state = (addr_bit<<SDA_SHIFT) | CS | SCLK
		
			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
		for j in range(data.shape[0]):
			data_bit = (data>>j)&1
			state = (data_bit<<SDA_SHIFT) | CS
			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)
			state =( data_bit<<SDA_SHIFT) | CS | SCLK	
			self.snap.write_int('adc16_controller',state,offset=0,blindwrite=True)		
		
		self.snap.write_int('adc16_controller',IDLE,offset=0,blindwrite=True)

	def reset(self):
                self.write_adc(0x00,0x0001)
                                                                                                                                    
	def power_down(self):
                self.write_adc(0x0f,0x0200)	
	def power_up(self):
                self.write_adc(0x0f,0x0000)
       
#	def supports_demux(self):
#                #adc16_controller supports demux modes if the W bit(0x04000000) is not set to 1 so this function returns true if
#                #adc16_controller supports demux modes (set by the firmware)
#                #self.snap.write_int('adc16_controller',self.snap.read_int('adc16_controller',offset=1)
#                #first write the bit, then read it, if it's NOT there anymore then setting demux mode is supported  
#                #Setting W bit to 1:
#                self.snap.write_int('adc16_controller', 0x0400_0000, offset=1)
#                #reading adc16_controller and returing True if it is 0, which means that W bit could not be written to
#                return (self.snap.read_int('adc16_controller',offset=1)==0)
        
	def set_demux(self, **kwargs):
                if self.kwargs['demux_mode']==1:
                        self.write_adc(0x31,0x0001)
                elif self.kwargs['demux_mode']==2:
                        self.write_adc(0x31,0x0102)
                elif self.kwargs['demux_mode']==4:
                        self.write_adc(0x31,0x0204)
                else:
                        print('Invalid or no demux mode specified')
                        exit(1)


#	def adc16_based(self,**kwargs):
#                for i in self.snap.listdev():
#                        if i == 'adc16_controller':
#                                print('Design is ADC16-based')
#                        else:
#                                print('Programmed %s with bof file, but design is not ADC16-based'%self.kwargs['host'])
#                                exit(1)



	def enable_pattern(self,pattern):                                                                                           
                if pattern=='ramp':
                        self.write_adc(0x25,0x0040)
                elif pattern=='deskew':
                        self.write_adc(0x25,0x0001)
                elif pattern=='sync':
                        self.write_adc(0x25,0x0002)
                else:
                        print('Pattern specified not found, possible options: ramp, deskew and sync')
                        exit(1)


	def read_ram(self,device):
		SNAP_REQ = 0x00010000
		bin_data = []
		self.snap.write_int('adc16_controller',0, offset=1)
		self.snap.write_int('adc16_controller',SNAP_REQ, offset=1)
		#Read the device that is passed to the read_ram method,1024 elements at a time,snapshot is a binary string that needs to get unpacked
		#Part of the read request is the size parameter,1024, which specifies the amount of bytes to read form the device
		snapshot = self.snap.read(device,1024,offset=0)
		
		#struct unpack returns a tuple of signed int values. 
		#Since we're requesting to read adc16_wb_ram at a size of 1024 bytes, we are unpacking 
		#1024 bytes each of wich is b, signed char(in C, python only knows ints). Unpacking as
		#a signed char is for mapping purposes:

		# ADC returns values from 0 to 255 (since it's an 8 bit ADC), the voltage going into ADC
		# varies from -1V to 1V, we want 0 to mean 0, not -1 volts so we need to remap the output 
		# of the ADC to something more sensible, like -128 to 127. That way 0 volts corresponds to 
		# a 0 value in the unpacked data. 
		string_data = struct.unpack('>1024b', snapshot)
#	 	print(type(string_data))
#		print(type(string_data[0]))
		#Converting the tuple into a vector of 1024 elements
		array_data = np.array(string_data)
#		print(array_data.dtype)	
#		print(array_data)
#		for i in range(array_data.shape[0]):
#			print('{:08b}'.format(array_data[i]))	
		#print(array_data)
		return array_data
#			
#			
#			x = bin(array_data[i])
#			print('{:>010b}'.format(x))
#		print(array_data.shape)
#		j = 0
#		k = 1
#		while j < 1024:
#			print('{:08b}'.format(array_data[j]))	
#			print('{:08b}'.format(array_data[k]))	
#			j += 8
#			k += 8
	#function that tests taps, it shifts data checks with the expected data and ouputs the error count

	
	#The ADC16 controller word (the offset in write_int method) 2 and 3 are for delaying taps of A and B lanes, respectively.
	#Refer to the memory map word 2 and word 3 for any calirification. The memory map was made for a ROACH design so it has chips A-H. 
	#SNAP 1 design has three chips
	
##	def chip_select(self, chip):
#		if chip =='A'|'a':
#			self.snap.write_int('adc16_controller', 1, offset=1)
#		elif chip

	def delay_tap(self,tap):
		delay_tap_mask = 0x1f
		self.snap.write_int('adc16_controller', 0 , offset = 2)
		self.snap.write_int('adc16_controller', 0 , offset = 3)
		#Set tap bits
		self.snap.write_int('adc16_controller', delay_tap_mask & tap , offset = 1)
		#Set strobe bits
		self.snap.write_int('adc16_controller', 0xfff, offset = 2)
		self.snap.write_int('adc16_controller', 0xfff, offset = 3)
		#Clear all bits
		self.snap.write_int('adc16_controller', 0 , offset = 1)
		self.snap.write_int('adc16_controller', 0 , offset = 2)
		self.snap.write_int('adc16_controller', 0 , offset = 3)
	

	#returns an array of error counts for a given tap(assume structure chan 1a, chan 1b, chan 2a, chan 2b etc.. until chan 4b
	def test_tap(self, tap):
		expected = 0x2a
		self.delay_tap(tap)
		#read_ram reuturns an array of data form a sanpshot from ADC output
		data = self.read_ram('adc16_wb_ram0')
		#each tap will return an error count for each channel and lane, so an array of 8 elements with an error count for each
		error_count = []

		chan1a_error = 0
		chan1b_error = 0
		chan2a_error = 0
		chan2b_error = 0
		chan3a_error = 0
		chan3b_error = 0
		chan4a_error = 0
		chan4b_error = 0
	
	
	
	
		i=0
		while i < 1024:
			if data[i] != expected:
				chan1a_error += 1
			if data[i+1] != expected:
				chan1b_error += 1
			if data[i+2] != expected:
				chan2a_error += 1
			if data[i+3] != expected:
				chan2b_error += 1
			if data[i+4] != expected:
				chan3a_error += 1

			if data[i+5] != expected:
				chan3b_error += 1
			if data[i+6] != expected:
				chan4a_error += 1
			if data[i+7] != expected:
				chan4b_error += 1
			i += 8

		return([chan1a_error, chan1b_error, chan2a_error, chan2b_error, chan3a_error, chan3b_error, chan4a_error, chan4b_error])

	def walk_taps(self):
		self.enable_pattern('deskew')
		error_list = []
		for tap in range(32):
			error_list.append(self.test_tap(tap))
		good_tap_range = []	
		best_tap_range = []
#		print(error_list)
		min_tap=[]
		max_tap=[]
		#This loop is kind of convoluted but it basically goes through error_list, finds the elements with a value of 0 and appends them to a new list 
		#It also picks out the elements corresponding to different channels and groups them together. The error_list is a list where each 'row' is a different tap
		#I wanted to find the elements in each channel that have zero errors, group the individual channels, and get the value of the tap in which they're in - which is the index of the row

		for i in range(8):
			good_tap_range.append([])
			for j in range(32):
				if error_list[j][i]==0:
					good_tap_range[i].append(j)
	#	find the min and max of each element of good tap range and call delay tap with that 
	
		for k in range(8):
			min_tap = min(good_tap_range[k])
			max_tap = max(good_tap_range[k])

			best_tap = (min_tap+max_tap)/2

		#	self.delay_tap(best_tap)
		print(good_tap_range)
		
		
		

		#set the middle tap as the probably tap to make the most accurate pattern

		#delay_taps
		


		
#
#		k = 0
#		while k < 32:
#         		i=0
#         		good_tap_range.append([])
#			#print(k)
#          		while error_list[k][0]==0:
#                    		good_tap_range[j].append(i)
#                    		k +=1
#                    		i+=1	
#				j +=1	
#				print(k)
#
#			k+=1	
#		print(good_tap_range)
#


							
		#Test taps 0 and 31 first to see if they 
