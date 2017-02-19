## ADC16 calibrationa and control

This repository houses calibration and control scripts for the HMCAD1511 ADC chips on the CASPER SNAP board.

### Installation

To install, download and run

```
sudo python setup.py install
```

You will need the `numpy` and `katcp` python packages.

### Usage

To program a board and calibrate, from the command line, run:

```
snap_init snapname boffile [-d 1,2 or 4]
```

where `snapname` is the hostname / IP of SNAP board, `boffile` is the name of the bof to run, and `-d` selects the demux factor of either 1, 2 or 4. The script can be run with `-h` for more details on usage.

To program the board from a script:

```
from snap_control import SnapBoard
s = snap.SnapBoard(host, katcp_port, timeout=10)
s.program(boffile=bof, 
          chips=chips, 
          demux_mode=demux_mode, 
          gain=gain)
```

