# Generalisation of LATCH ABM Project (Open Trip Planner)
Original implementation at https://bitbucket.org/dhixsingh/latch-abm/src/master/otp/

The ./run-otp.sh script is a wrapper function for running OpenTripPlanner <http://www.opentripplanner.org/>, as configured using odm.py.  It is used to calculate OD matrices for a given set of data, according to a range of optional parameters dictating  sequence of times of day and multimodal trip combinations.

This script has been modified from the original version to seek out project resources in a specified directory in the ./graphs/ path.  In this project directory you would locate your GTFS, OpenStreetMap and (optionally) GeoTiff elevation data.

## Usage

usage: run-otp.sh [options]

options:
```
-h       Print this help.
-v       Show commands being executed

-d       Specify project directory (req'd); files are assumed to be located here.  This is a subfolder of /graphs/
    
-p       Specify pbf file for osm data; assumed within project dir.

-t       Specify GTFS zip file name; assumed within project dir

-x       Build the graph
-w ARGS  optional arguments:
         -h, --help            show this help message and exit
         --departure_time DEPARTURE_TIME
                               departure time - format YYYY-MM-DD-HH:MM:SS
         --duration_reps DURATION_REPS DURATION_REPS
                               Two optional parameters defining a time duration and a
                               repeat interval in hours
         --proj_dir PROJ_DIR   project directory
         --originsfile ORIGINSFILE
                               path to the input csv file, which contains coordinates
                               of origins
         --destsfile DESTSFILE
                               path to the input csv file, which contains coordinates
                               of destinations
         --outfile OUTFILE     path to the output csv file (default:
                               traveltime_matrix)
         --max_time MAX_TIME   maximum travel time in seconds (default: 7200)
         --max_walking_distance MAX_WALKING_DISTANCE
                               maximum walking distance in meters (default: 500)
         --mode_list [MODE_LIST [MODE_LIST ...]]
                               Modes to travel by. Options --pending appropriate
                               data-- are: WALK, BICYCLE, CAR, TRAM, SUBWAY, RAIL,
                               BUS, FERRY, CABLE_CAR, GONDOLA, FUNICULAR, TRANSIT,
                               LEG_SWITCH, AIRPLANE (default: WALK,BUS,RAIL)
         --matching MATCHING   How origins and destinations should be matched. Can be
                               either one-to-one or one-to-many (default: one-to-
                               many)
         --combinations        Create all combinations of supplied destination list
         --wideform            Transpose data to wideform from longform main output

-r       run Open Trip Planner (use -x too if needed)
```

Here is an example of what a call to odm.py without using the run-otp.sh wrapper looks like:
```
java -cp otp-0.19.0-shaded.jar:jython-standalone-2.7.0.jar org.python.util.jython odm.py --departure_time 2018-09-12-07:30:00 --duration_reps 2 .5 --originsfile graphs/aus_vic_melb_20180911/SA2_origins_manual.csv --destsfile graphs/aus_vic_melb_20180911/SA2_destinations_manual.csv --outfile graphs/aus_vic_melb_20180911/SA2_SA2_ODM_repetition_test2.csv --mode_list 'WALK,TRANSIT' --proj_dir ./graphs/aus_vic_melb_20180911
```
Or, using the run-otp.sh wrapper function (which unlike the above, will build the graph.obj required for analysis if not yet built):

```
./run-otp.sh  -d aus_vic_melb_20180911 -p melb_gccsa_2016_10000m_20180208.pbf -t gtfs_aus_vic_melb_20180911.zip -w "--departure_time 2018-09-12-07:30:00 --originsfile graphs/aus_vic_melb_20180911/SA2_origins_manual.csv --destsfile graphs/aus_vic_melb_20180911/SA2_destinations_manual.csv --outfile graphs/aus_vic_melb_20180911/SA2_SA2_ODM_repetition_test2.csv --mode_list 'WALK,TRANSIT'"
```

There is an assumption that GTFS.zip, osm.pbf and (optionally) .tif data are stored in the./graphs/project_folder directory.


## Prerequisites
* Jython 2.7 (Download jython-installer-2.7.0.jar from http://www.jython.org/downloads.html)
        > java -jar jython-installer-2.7.0.jar

* OTP 0.9.0 jar file ( download from http://docs.opentripplanner.org/en/latest/Getting-OTP/#pre-built-jars)
* OpenStreetMap portion for your study region 
** .pbf format recommended
** you can use Osmosis to extract a subset using a .poly boundary file
** make sure to buffer any study region boundary by an appropriate amount (say, 10km) to account for edge effects (e.g. truncated road network connectivity)
* GTFS transport data (e.g. see http://transitfeeds.com/) with appropriate spatial coverage of your study region

Original authour (LATCH ABM): Dhirendra Singh, 2016-18
Modified: Carl Higgs, 2018

