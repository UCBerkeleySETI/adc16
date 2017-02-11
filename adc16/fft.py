import struct
import corr
import time
import numpy as np
import matplotlib.pyplot as plt


print('Connecting to FPGA.......\n')
a = corr.katcp_wrapper.FpgaClient('10.0.1.221')
#a.progdev('adctestJack.bof')
time.sleep(1)
print(a.is_connected())


snapshot = a.snapshot_get('snapshot',man_trig=True, man_valid=True)
x = struct.unpack('>%db'%snapshot['length'],snapshot['data'])


#DEMUX by 1
a = np.zeros(snapshot['length']/4)
a = x[0::4]
plt.plot(a)
plt.show()


#DEMUX by 4
#plt.plot(x)
#plt.show()



#DEMUX by 2 code
#a = np.zeros(snapshot['length']/2)
#a[0::2] = x[0::4]
#a[1::2] = x[1::4]
#
#
#
#b = np.fft.fftshift(np.fft.fft(a))
#plt.plot((np.abs(b))**2)
#
#plt.plot(a,'-o')
#plt.show()
#

