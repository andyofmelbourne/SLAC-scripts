# xtcav_laseroff
Calibrates psana for xtcav analysis and puts the info into a psana calib folder.

### Usage
```
$ python xtcav_laseroff.py -h
usage: xtcav_laseroff.py [-h] [-c CONFIG] [-e EXPERIMENT] [-r RUN]
                         [-m MAXSHOTS] [-o OUTPUT] [-b BUNCHES]

write laser off calibration for xtcav to calib

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        file name of the configuration file
  -e EXPERIMENT, --experiment EXPERIMENT
                        psana experiment string (e.g cxi01516)
  -r RUN, --run RUN     experiment run/s (e.g 101 or 101-110)
  -m MAXSHOTS, --maxshots MAXSHOTS
                        maximum number of frames to process (e.g 5000)
  -o OUTPUT, --output OUTPUT
                        output directory for the psana calib files (by default
                        this goes into the experiment calib)
  -b BUNCHES, --bunches BUNCHES
                        number of xray bunches in each frame (e.g 1 or 2)
```

You can also submit a SLAC batch job:
```
$ bsub -q psanaq -a mympi -n 32 -o test.out python xtcav_laseroff.py -c config.ini 
```
to check the status of your jobs:
```
$ bjobs -w -a
```
and to see the output of the running job:
```
$ tail -f test.out
```

You can supply the psana data source and output file stuff through the config.ini file:
```
[source]
exp = xpptut15
runs = 101

[params]
maxshots = 1000
output   = None 
```
or the command line:
```
$ python xtcav_laseroff.py -e xpptut15 -r 101
```
