# Multi-modal Origin-Destination analysis for 30 minute cities using OpenTripPlanner
This repository stores wrapper function scripts for running OpenTripPlanner; in particular, it is geared to facilitate analysis from origins to destinations using multiple modes and timepoints, with results output in long form to an SQLite database.  

The intent is to use these scripts to estimate the spatiotemporal distribution of time from communities (e.g. SA1 centroids) to employment hubs (DZN centroids), considering variation across mode choice/mix and departure time.

It is a generalisation and reapplication of the LATCH ABM Project, found at https://bitbucket.org/dhixsingh/latch-abm/src/master/otp/

The ./run-otp.sh script is a wrapper function for running OpenTripPlanner <http://www.opentripplanner.org/>, as configured using odm.py.  It is used to calculate OD matrices for a given set of data, according to a range of optional parameters dictating  sequence of times of day and multimodal trip combinations.

This script has been modified from the original version to seek out project resources in a specified directory in the ./graphs/ path.  In this project directory you would locate your GTFS, OpenStreetMap and (optionally) GeoTiff elevation data.

The OpenTripPlanner implementation was adapted by Carl Higgs from original code authored Dr Dhirendra Singh through the 'Decision making for lifetime affordable and tenable city housing' project under an ARC Linkage grant, LP130100008, and whose contribution of the code for this project we gratefully acknowledge.  

## Usage

usage: run-otp.sh [options]

options:
```
usage: run-otp.sh [options]

  options:
    -h       Print this help.
    -v       Show commands being executed
    -d       Specify project directory (reqd); files are assumed to be located here.
             This is a subfolder of ./graphs/
    -p       Specify pbf file for osm data; assumed within project dir.
    -t       Specify GTFS zip file name; assumed within project dir
    -x       Build the graph
    -w ARGS  Build a origin-destination matrix (CSV) using odm.py to drive OTP.
             The following arguments used to drive the analysis are passed to odm.py in quotes:
                optional arguments:
                  -h, --help            show this help message and exit
                  --departure_time DEPARTURE_TIME
                                        departure time - format YYYY-MM-DD-HH:MM:SS
                  --duration_reps DURATION_REPS DURATION_REPS
                                        Two optional parameters defining a time duration and a
                                        repeat interval in hours.
                  --proj_dir PROJ_DIR   project directory
                  --originsfile ORIGINSFILE
                                        path to the input csv file, which contains coordinates
                                        of origins
                  --destsfile DESTSFILE
                                        path to the input csv file, which contains coordinates
                                        of destinations
                  --outdb OUTDB         path to the output sqlite database (default:
                                        traveltime_matrix)
                  --outtable OUTTABLE   path to the output sqlite database (default:
                                        traveltime_matrix)
                  --max_time MAX_TIME   maximum travel time in seconds (default: 7200)
                  --max_walking_distance MAX_WALKING_DISTANCE
                                        maximum walking distance in meters (default: 500)
                  --mode_list [MODE_LIST [MODE_LIST ...]]
                                        Modes to travel by. Options --pending appropriate
                                        data-- are: WALK, BICYCLE, CAR, TRAM, SUBWAY, RAIL,
                                        BUS, FERRY, CABLE_CAR, GONDOLA, FUNICULAR, TRANSIT,
                                        LEG_SWITCH, AIRPLANE (default: WALK,BUS,RAIL)
                  --run_once [RUN_ONCE [RUN_ONCE ...]]
                                        Modes for which transport is only evaluated at one
                                        time point. For example, you may be evaluating
                                        difference between on-peak and off-peak travel times,
                                        however no difference would be expected for walking or
                                        cycling, so these may be excluded (e.g. WALK BICYCLE).
                                        Valid options are as per mod_list; the default is an
                                        empty list.
                  --matching MATCHING   How origins and destinations should be matched. Can be
                                        either one-to-one or one-to-many (default: one-to-
                                        many)
                  --combinations        Create all combinations of supplied destination list
                  --id_names [ID_NAMES [ID_NAMES ...]]
                                        Names of respective ID fields for source Origin and
                                        Destination csv files (default: GEOID GEOID)
                  --latlon_names [LATLON_NAMES [LATLON_NAMES ...]]
                                        Names of latitude and longitude fields in source
                                        Origin and Destination csv fields (default: lat lon)
                  --wideform            Transpose data to wideform from longform main output
                  --cmd CMD             The command used to call the python script may be
                                        specified; if so it is recorded to the log txt file.
    -r       run Open Trip Planner (use -x too if needed)
```

There is an assumption that GTFS.zip, osm.pbf and (optionally) .tif data are stored
in the./graphs/project_folder directory.

Here is an example of usage at the Bash shell prompt, first storing odm.py args in a variable
odm_args, and then executing:

```
odm_args="--departure_time 2018-09-27-08:00:00                                               \
          --duration_reps 2 2                                                                \
          --max_time 7200                                                                    \
          --max_walking_distance 500                                                         \
          --matching one-to-many                                                             \
          --originsfile graphs/sa1_dzn_modes_melb_2016/SA1_2016_melb_gccsa_10km_epsg4326.csv \
          --destsfile graphs/sa1_dzn_modes_melb_2016/DZN_2016_melb_gccsa_10km_epsg4326.csv   \
          --outdb graphs/sa1_dzn_modes_melb_2016/SA1_DZN_2016_melb_gccsa_10km.db             \
          --outtable od_6modes_8am_10am                                                      \
          --mode_list WALK BICYCLE CAR 'WALK,BUS' 'WALK,TRAM' 'WALK,RAIL' 'WALK,TRANSIT'     \
          --run_once WALK BICYCLE CAR                                                        \
          --id_names SA1_MAINCODE_2016 DZN_CODE_2016                                         \
          --latlon_names Y X                                                                 \
          --wideform                                                                         \
          --proj_dir ./graphs/sa1_dzn_modes_melb_2016"

./run-otp.sh  -d sa1_dzn_modes_melb_2016              \
              -p melb_gccsa_2016_10000m_20180208.pbf  \
              -t gtfs_aus_vic_melb_20180911.zip -w    \
              "$odm_args"
```

## Prerequisites
This has been successfully run on Ubuntu with openjdk version "1.8.0_181" of java installed.  These are the main installation pre-requisites, otherwise, you need to make sure the following jar files are located in the project directory, and other data is present and specified as required:

* Jython 2.7 (Download ython-standalone-2.7.0.jar from https://www.jython.org/downloads.html and co-locate other jars in project directory)
* OTP 0.9.0 jar file ( download from http://docs.opentripplanner.org/en/latest/Getting-OTP/#pre-built-jars)
* Xerial sqlite jar from https://bitbucket.org/xerial/sqlite-jdbc/downloads/sqlite-jdbc-3.23.1.jar to be located along with the otp and jython jars
* OpenStreetMap portion for your study region 
    * .pbf format recommended
    * you can use Osmosis to extract a subset using a .poly boundary file
    * you can create a .poly boundary file from a spatial feature in EPSG 4326 CRS using QGIS with the osmpoly_export plugin
    * make sure to buffer any study region boundary by an appropriate amount (say, 10km) to account for edge effects (e.g. truncated road network connectivity) before making the .poly file
* GTFS transport data (e.g. see http://transitfeeds.com/) with appropriate spatial coverage of your study region
* optional elevation data (e.g. from https://www.eorc.jaxa.jp/ALOS/en/aw3d30/)
    * I believe you should merge your .tif tiles into one .tif; you can do this using GDAL merge, but it may be easier to use the wrapper python script i wrote bulk_gdal_merge.py

Original authour (LATCH ABM): Dhirendra Singh, 2016-18

Modified: Carl Higgs, 2018

