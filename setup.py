#!/usr/bin/env python
"""
setup.py -- setup script for fits2hdf package
"""
from setuptools import setup, find_packages

version = '1.0.0'

# create entry points
# see http://astropy.readthedocs.org/en/latest/development/scripts.html
entry_points = {
    'console_scripts' :
        ['adc16_init = adc16.adc16_init:cmd_tool',
     ]
    }

setup(name='adc16',
      version=version,
      description='HMCAD1511 ADC chip calibration module',
      install_requires=['numpy', 'corr'],
      url='https://github.com/ucberkeleyseti/adc16',
      author='Zuhra Abdurashidova and friends',
      entry_points=entry_points,
      packages=find_packages(),
      zip_safe=False,
      )
