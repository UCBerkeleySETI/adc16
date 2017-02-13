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
        ['snap_init = snap_board.snap_init:cmd_tool',
     ]
    }

setup(name='snap_board',
      version=version,
      description='HMCAD1511 ADC chip calibration module',
      install_requires=['numpy', 'corr'],
      url='https://github.com/ucberkeleyseti/snap_board',
      author='Zuhra Abdurashidova and friends',
      entry_points=entry_points,
      packages=find_packages(),
      zip_safe=False,
      )
