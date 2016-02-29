# xtcav_powerstack
Get the xray power vs time profile for every shot and save it to a h5 file (along with a bunch of other stuff).

### Usage
```
$ ssh psna
$ source /reg/g/psdm/etc/ana_env.sh (or .csh)
$ python xtcav_powerstack.py -h
usage: xtcav_powerstack.py [-h] [-c CONFIG]

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

### Output
```
$ h5ls -r xpptut15-r0124-xtcav-powerstack.h5 
/                        Group
/delay                   Dataset {10/Inf, 1}
/delay_gaus              Dataset {10/Inf, 2}
/energyperpulse          Dataset {10/Inf, 1}
/event_number            Dataset {10/Inf}
/image_fs_scale          Dataset {10/Inf}
/image_mev_scale         Dataset {10/Inf}
/ok                      Dataset {10/Inf}
/power                   Dataset {10/Inf, 1, 72}
/power_ebeam             Dataset {10/Inf, 100}
/power_ecom              Dataset {10/Inf, 1, 72}
/power_erms              Dataset {10/Inf, 1, 72}
/reconstruction_agreement Dataset {10/Inf}
/time                    Dataset {10/Inf, 1, 72}
/timestamp               Dataset {10/Inf}
/xtcav_image             Dataset {10/Inf, 1, 350, 100}
```

### config.ini 
```
[source]
exp  = xpptut15
run  = 124
mode = 'smd'

[params]
calib          = '../calib'
maxshots       = None
bunches        = 1 
chunksize      = 100
process_every  = 1
delay_bound    = 100. 

[output]
h5fnam     = 'exp-run-xtcav-powerstack.h5' 
matchfnam  = True
h5dir      = './'
#h5dir      = '/reg/d/psdm/CXI/cxi01516/scratch/amorgan/xtcav/'

# xray power vs delay 
power           = True
# xray power vs delay with the 'com method'
power_ecom      = True
# xray power vs delay with the 'rms method'
power_erms      = True
# electron current vs delay
power_ebeam     = True
# time (or delay) values (in femto-seconds) for the above plots
time            = True
# delay as calculated by psana 
delay           = True
# delay calculated by fitting two gaussians to 'power'
delay_gaus      = True
# delay calculated by fitting two gaussians to 'power'
energyperpulse  = True
# event timestamps as a big string
timestamp       = True
# processed electron bunch images from the xtcav
xtcav_image     = True
# event number of the file stream (absolute)
event_number    = True
# fs / pixel of the xtcav image (fast scan)
image_fs_scale  = True
# MeV / pixel of the xtcav image (slow scan)
image_MeV_scale = True
# the reconstruction agreement parameter = normalised dot product of 'power_ecom' and 'power_ebeam' (-1 --> 1)
reconstruction_agreement = True
```
for full documentation please read the source code of this script and all of the psana dependencies, click 'I agree' after reading all of that.

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
$ cd /reg/d/psdm/cxi/cxij6916/scratch/xtcav/SLAC-scripts/xtcav/powerstack
$ mpirun -np 16 python xtcav_powerstack.py -c config.ini
```

#### GUI    
For the gui you will need X forwarding which the above does not provide:
```
$ bsub -q psfehhiprioq -n 16 -Is /bin/bash 
```
not the psana machine you log into (e.g. psana1606) then open a new terminal and run:
```
$ ssh -X psana1606
$ source /reg/g/psdm/etc/ana_env.sh 
$ cd /reg/d/psdm/cxi/cxij6916/scratch/xtcav/SLAC-scripts/xtcav/powerstack
$ mpirun -np 2 python xtcav_gui.py -c config_gui.ini
```
Note: this is now tested.
