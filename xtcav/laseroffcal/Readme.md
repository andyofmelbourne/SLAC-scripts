# xtcav_laseroff
Calibrates psana for xtcav analysis and puts the info into a psana calib folder.

This is required to run any of the advanced psana modules for the lasing on events.

### Usage
```
$ ssh psna
$ source /reg/g/psdm/etc/ana_env.sh (or .csh)
$ cd /reg/d/psdm/cxi/cxij6916/scratch/xtcav/SLAC-scripts/xtcav/laseroffcal
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

### Batch Jobs
You can also submit a SLAC batch job:
```
$ ssh psana
$ source /reg/g/psdm/etc/ana_env.sh (or .csh)
$ cd /reg/d/psdm/cxi/cxij6916/scratch/xtcav/SLAC-scripts/xtcav/laseroffcal
$ bsub -q psanaq -a mympi -n 32 -o test.out python xtcav_laseroff.py -c config.ini 
```
or, if your experiment is currently running and this is important, for the near-experimental-hall:
```
$ bsub -q psnehhiprioq -a mympi -n 32 -o test.out python xtcav_laseroff.py -c config.ini
```
for the far-experimental-hall:
```
$ bsub -q psfehhiprioq -a mympi -n 32 -o test.out python xtcav_laseroff.py -c config.ini
```
to check the status of your jobs:
```
$ bjobs -w -a
```
and to see the output of the running job:
```
$ tail -f test.out
```
It is also possible to reserve some high priority cores in an interactive session:
```
$ bsub -q psfehhiprioq -n 16 -Is /bin/bash 
$ mpirun -np 16 python xtcav_laseroff.py -c config.ini
```
Note: this is untested.
