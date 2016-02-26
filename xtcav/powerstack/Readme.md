# xtcav_powerstack
Get the xray power vs time profile for every shot and save it to a h5 file.

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
  -e EXPERIMENT, --experiment EXPERIMENT
                        psana experiment string (e.g cxi01516)
  -r RUN, --run RUN     experiment run/s (e.g 101 or 101-110)
  -m MODE, --mode MODE  psana access mode (smd for semi-online)
  -d H5DIR, --h5dir H5DIR
                        output director for the h5 file.
  -f H5FNAM, --h5fnam H5FNAM
                        output file name for the h5 file.
  --matchfnam MATCHFNAM
                        use regular expression to match 'exp' and 'run' in the
                        filename.
  -b BUNCHES, --bunches BUNCHES
                        number of xray bunches in each frame (e.g 1 or 2)
```

You can also submit a SLAC batch job:
```
$ bsub -q psanaq -a mympi -n 32 -o test.out python xtcav_powerstack.py -c config.ini 
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
or the command line:
```
$ python xtcav_powerstack.py -e xpptut15 -r 124
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

