# darkcal
Takes the raw sum of all frames in a run.

### Usage
```
$ python darkcal.py -h
usage: mpirun -np [NUM] [OPTIONS] darkcal.py [-h] [-c CONFIG] [-s SOURCE]

print slac psana event variables

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        file name of the configuration file
  -s SOURCE, --source SOURCE
                        psana source string (e.g exp=cxi01516:run=10:idx)
```

Although it would be better if you used SLACs batch jobs system:
```
$ bsub -q psanaq -a mympi -n 32 -o test.out python darkcal.py -c config.ini
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

[output]
# here "exp" is replaced with the above variable [source][exp] 
# and "run" with r00[source][run] but only if match is True
fnam   = 'exp-run-CsPad-darkcal.h5' 
match  = True
h5path = 'data/data'
h5dir  = '/reg/d/psdm/CXI/cxi01516/scratch/amorgan/darkcal/'
```
or the command line:
```
$ mpirun -np 4 python psana_event_inspection.py -s exp=cxi01516:run=14:idx
```
in which case the config.ini file is used for all other parameters.


### Trouble shooting
* Something wrong with the psana source? Check that you have set detector_psana_source and detector_psana_type correctly with SLAC-scripts/psana_event_inspection.
* Will not output with slab = True? This is probably because the LCLS has done something funny with the data shapes. Or it could be because you are looking at pnccd data (not implimented yet).
* Why not look at the slab shaped or geometry corrected output? You can use https://github.com/andyofmelbourne/CsPadMaskMaker.git to do this.

