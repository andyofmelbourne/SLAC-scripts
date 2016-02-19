# psana_event_inspection
Just screen dumps:
* epics pvNames 
* epics aliases 
* psana data type and source  

variables for the first event in a given run.

### Usage
```
$ python psana_event_inspection.py -h
usage: psana_event_inspection.py [-h] [-c CONFIG] [-s SOURCE]

print slac psana event variables

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        file name of the configuration file
  -s SOURCE, --source SOURCE
                        psana source string (e.g exp=cxi01516:run=10:idx)
```

You can supply the psana data source through the config.ini file:
```
[source]
exp  = cxi01516
runs = 16
```
or the command line:
```
$ python psana_event_inspection.py -s exp=cxi01516:run=16:idx
```

