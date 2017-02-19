from snap_control import SnapBoard
import logging

print('Connecting to SNAP...')
s = SnapBoard('rpi-bl')

print('Programming with test firmware...')
s.progdev('test_adc16_2016-8-26_1131.bof')

print('Initializing ADCs...')
s.adc.initialize(chips='all', gain=1, demux_mode=1)

print('Calibrating...')
s.adc.logger.setLevel(logging.INFO)
s.adc.calibrate()

print('DONE.')
exit()