__This repo contains BL-specific code, unlikely to be useful outside the project. Newer users of CASPER SNAP boards should check out [casper-astro/casperfpga](https://github.com/casper-astro/casperfpga)__

## ADC16 calibration and control

This repository houses calibration and control scripts for the HMCAD1511 ADC chips on the CASPER SNAP board.

### Installation

To install, download and run

```
sudo python setup.py install
```

You will need the `numpy` and `katcp` python packages.

### Command-line Usage

##### Program SNAP
To program a board and calibrate, from the command line, run:

```
snap_init snapname boffile [-d 1,2 or 4]
```

where `snapname` is the hostname / IP of SNAP board, `boffile` is the name of the bof to run, and `-d` selects the demux factor of 
```
snap_init HOST BOF_FILE [OPTIONS]

positional arguments:
  host                  specify the host name
  bof                   specify the bof file to load unto FPGA

optional arguments:
  -h, --help            show this help message and exit
  -d DEMUX_MODE, --demux DEMUX_MODE
                        Set demux mode 1/2/4
  -g GAIN, --gain GAIN  Possible gain values (choose one): { 1 1.25 2 2.5 4 5
                        8 10 12.5 16 20 25 32 50 }, default is 1
  -k KATCP_PORT, --katcp_port KATCP_PORT
                        KATCP port to use (default 7147)
  -c CHIPS [CHIPS ...], --chips CHIPS [CHIPS ...]
                        Input chips you wish to calibrate. Default all chips:
                        a b c.
  -s, --silent          Silence all logging info.
  -v, --verbose         Verbose mode, for debugging.
```

##### Plot SNAP ADC data

To plot data from the ADCs from the command line, run:

```
snap_plot snapname [options]

positional arguments:
  host                  specify the host name

optional arguments:
  -h, --help            show this help message and exit
  -p KATCP_PORT, --port KATCP_PORT
                        KATCP port to connect to (default 7147)
  -d DEMUX_MODE, --demux DEMUX_MODE
                        ADC demux mode (1, 2 or 4)
  -r, --remote          Faster plotting for remote connection
  -f, --fft             Plot ADC channel bandpass (i.e. take FFT^2 of snapshot
                        data)
  -T, --deskewpattern   Plot test pattern (deskew). Value should be a constant
                        42.
  -R, --ramppattern     Plot test pattern (ramp)
```
  
### Script usage

To program the board from a script:

```python
from snap_control import SnapBoard

s = snap.SnapBoard(host, katcp_port, timeout=10)
s.program(boffile=bof, 
          chips=chips, 
          demux_mode=demux_mode, 
          gain=gain)
```


