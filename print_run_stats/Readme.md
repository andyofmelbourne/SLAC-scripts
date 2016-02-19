# run_stats.py
Loops through runs and prints various e.g.:
* event id 
* time stamps
* photon energy 
* run time in seconds
* ...

for the first event in each run. This is mainly designed so that you can just copy and paste the values from the terminal into (say) a google spreadsheet. 


### Usage
```
$ python run_stats.py -h
usage: run_stats.py [-h] config

print slac run statistics (e.g. to put into a spreadsheet)

positional arguments:
  config      file name of the configuration file

optional arguments:
  -h, --help  show this help message and exit
```

You can supply the psana data source, output params and epics sources through the config.ini file:
```
[source]
exp = cxi01516
runs = 1-51

[output]
id            = False
events        = False
z_stage       = False
pulse_length  = False
photon_energy = True
seconds       = False
hms           = False
date          = False
st            = False

[epics]
z_stage = 'CXI:DS2:MMS:06.RBV'
pulse_length = 'SIOC:SYS0:ML00:AO820'
```

#### Example output:
In this example run_stats.py attempts to print the photon energy (in keV) for runs 1 to 51 (inclusive). 
```
$ python run_stats.py config.ini 
exp=cxi01516:run=1-51:idx
data source exp=cxi01516:run=1-51:idx
photon_energy 	

0.647127500624 
0.64816019704 
0.64605860779 
0.646335400752 
0.64540520892 
0.662655163878 
0.700952781298 
0.700952781298 
could not extract any events for run: 9
could not extract any events for run: 10
7.20024900638 
7.21134698849 
7.21239707127 
7.20712422249 
7.20113346901 
7.20853498016 
7.21185046817 
7.21790331108 
7.20426374159 
7.20855807986 
7.2015309003 
7.205072326 
7.20590056964 
7.21181889087 
7.2161864486 
7.2067208443 
7.20368401618 
7.21174610932 
7.21890383383 
7.21599494139 
7.20765830836 
7.20361040707 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
NA 
6.88954958596 
```
The 'NA' values are because the photon energy could not be extracted from the events those runs and the 'could not extract any events for run: 10' values are because no events at all could be extracted.

