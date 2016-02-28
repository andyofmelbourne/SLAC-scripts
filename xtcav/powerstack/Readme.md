# xtcav_powerstack
Get the xray power vs time profile for every shot and save it to a h5 file (along with a bunch of other stuff).

### Usage
```
usage: xtcav_powerstack.py [-h] [-c CONFIG] [-e EXPERIMENT] [-r RUN] [-m MODE]
                           [-d H5DIR] [-f H5FNAM] [--matchfnam MATCHFNAM]
                           [-b BUNCHES]

Get the xray power vs time profile for every shot

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        file name of the configuration file
```

run with or without mpi:
```
$ python xtcav_powerstack.py -c config.ini
$ mpirun -n 3 python xtcav_powerstack.py -c config.ini
```

You can supply the psana data source and output file stuff through the config.ini file:
```
[source]
exp = xpptut15
run = 124

[params]
calib     = '../calib'
maxshots  = None
bunches   = 1 
mode      = 'smd'
chunksize = 100

[output]
h5fnam     = 'exp-run-xtcav-powerstack.h5' 
matchfnam  = True
#h5dir      = '/reg/d/psdm/CXI/cxi01516/scratch/amorgan/xtcav/'
h5dir      = './'
```

### Output
```
$ h5ls -r xpptut15-r0124-xtcav-powerstack.h5 
/                        Group
/delay                   Dataset {3400/Inf, 1}
/energy_per_pulse        Dataset {3400/Inf, 1}
/event_number            Dataset {3400/Inf, 1, 72}
/event_numbers           Dataset {3400/Inf}
/time_fs                 Dataset {3400/Inf, 1, 72}
/timestamp               Dataset {3400/Inf}
/xray_power              Dataset {3400/Inf, 1, 72}
```

### Config.ini File



### Batch Job
You can also submit a SLAC batch job:
```
$ bsub -q psanaq -a mympi -n 32 -o test.out python xtcav_powerstack.py -c config.ini 
```
or, if your experiment is currently running and this is important, for the near-experimental-hall:
```
$ bsub -q psnehhiprioq -a mympi -n 32 -o test.out python xtcav_powerstack.py -c config.ini
```
for the far-experimental-hall:
```
$ bsub -q psfehhiprioq -a mympi -n 32 -o test.out python xtcav_powerstack.py -c config.ini
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
$ mpirun -np 16 python xtcav_powerstack.py -c config.ini
```
Note: this is untested.
