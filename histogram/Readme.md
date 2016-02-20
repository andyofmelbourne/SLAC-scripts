# makehist
calculate the adu histogram of a run

Note: this script only works with 4 cores.
### Usage
```
$ python makehist.py -h
usage: mpirun -np 4 [OPTIONS] makehist.py [-h] [-c CONFIG] [-s SOURCE]

calculate the adu histogram of a run

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        file name of the configuration file
  -s SOURCE, --source SOURCE
                        psana source string (e.g exp=cxi01516:run=10:idx)
```

Although it would be better if you used SLACs batch jobs system:
```
$ bsub -q psanaq -a mympi -n 4 -o test.out python makehist.py -c config.ini
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
exp = cxi01516
run = 14
detector_psana_source = 'DetInfo(CxiDs2.0:Cspad.0)'
detector_psana_type = 'psana.CsPad.DataV2'

[histogram]
darkcal      = '/reg/d/psdm/CXI/cxi01516/scratch/amorgan/darkcal/cxi01516-r0014-CsPad-darkcal.h5'
hist_dtype   = uint16
shape        = 4, 8, 185, 388
bins         = -100, 400
buffer_size  = 1000
buffer_dtype = float32

[output]
# here "exp" is replaced with the above variable [source][exp] 
# and "run" with r00[source][run] but only if match is True
fnam   = 'exp-run-CsPad-histogram.h5' 
match  = True
h5path = 'data/data'
h5dir  = '/reg/d/psdm/CXI/cxi01516/scratch/amorgan/histogram/'
slab   = True
```

or the command line:
```
$ mpirun -np 4 python makehist.py -s exp=cxi01516:run=14:idx
```
in which case the config.ini file is used for all other parameters.
