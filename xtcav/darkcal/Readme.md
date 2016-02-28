# xtcav_darkcal
Takes the raw sum of all xtcav frames in a run (and some other stuff) and puts into a psana calib folder for pedestals correction. 

### Usage
```
$ ssh psna
$ source /reg/g/psdm/etc/ana_env.sh (or .csh)
$ python xtcav_darkcal.py -h
usage: xtcav_darkcal.py [-h] [-c CONFIG] [-e EXPERIMENT] [-r RUN]
                        [-m MAXSHOTS] [-o OUTPUT]

write dark pedestals for xtcav to calib

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        file name of the configuration file
  -e EXPERIMENT, --experiment EXPERIMENT
                        psana experiment string (e.g cxi01516)
  -r RUN, --run RUN     experiment run/s (e.g 102 or 102-110)
  -m MAXSHOTS, --maxshots MAXSHOTS
                        maximum number of frames to process (e.g 5000)
  -o OUTPUT, --output OUTPUT
                        output directory for the psana calib files (by default
                        this goes into the experiment calib)
```

You can supply the psana data source and output file stuff through the config.ini file:
```
[source]
exp = xpptut15
run = 102

[params]
maxshots = 1000
output   = None 
```
or the command line:
```
$ python xtcav_darkcal.py -e xpptut15 -r 102

### Batch Job
You can also submit a SLAC batch job:
```
$ bsub -q psanaq -o test.out python xtcav_darkcal.py -c config.ini
```
or, if your experiment is currently running and this is important, for the near-experimental-hall:
```
$ bsub -q psnehhiprioq -o test.out python xtcav_darkcal.py -c config.ini
```
for the far-experimental-hall:
```
$ bsub -q psfehhiprioq -o test.out python xtcav_darkcal.py -c config.ini
```
to check the status of your jobs:
```
$ bjobs -w -a
```
and to see the output of the running job:
```
$ tail -f test.out
```
