#!/bin/bash

DIR=`dirname "$0"`

############################################################################
# Defaults
############################################################################
VERBOSE=0   # default, not verbose
BUILD_GRAPH=0   # default is to build the graph and run otp
RUN_OTP=0
CALCULATE_ODM=0

############################################################################
# Usage
#
#
############################################################################
usage() {
    cat << END_HELP
usage: $(basename $0) [options]

  options:
    -h       Print this help.
    -v       Show commands being executed
    -d       Specify project directory (req'd); files are assumed to be located here.  This is a subfolder of /graphs/ 
    -p       Specify pbf file for osm data; assumed within project dir.  
    -t       Specify GTFS zip file name; assumed within project dir
    -x       Build the graph
    -w ARGS  Build a origin-destination matrix (CSV), passing ARGS to the underlying script, e.g.:
             usage: odm.py [-h] --departure_time DEPARTURE_TIME
              [--duration_reps DURATION_REPS DURATION_REPS] --proj_dir
              PROJ_DIR --originsfile ORIGINSFILE --destsfile DESTSFILE
              [--outfile OUTFILE] [--max_time MAX_TIME]
              [--max_walking_distance MAX_WALKING_DISTANCE]
              [--mode_list [MODE_LIST [MODE_LIST ...]]] [--matching MATCHING]
              [--combinations] [--wideform] [--init]
              
              Generate origin destination matrix
              
              optional arguments:
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
                
                Here is an example of what a call to it without using the run-otp.sh wrapper looks like:
                java -cp otp-0.19.0-shaded.jar:jython-standalone-2.7.0.jar org.python.util.jython odm.py --departure_time 2018-09-12-07:30:00 --duration_reps 2 .5 --originsfile graphs/aus_vic_melb_20180911/SA2_origins_manual.csv --destsfile graphs/aus_vic_melb_20180911/SA2_destinations_manual.csv --outfile graphs/aus_vic_melb_20180911/SA2_SA2_ODM_repetition_test2.csv --mode_list 'WALK,TRANSIT' --proj_dir ./graphs/aus_vic_melb_20180911
                
                Or, using the run-otp.sh wrapper function:

                ./run-otp.sh  -d aus_vic_melb_20180911 -p melb_gccsa_2016_10000m_20180208.pbf -t gtfs_aus_vic_melb_20180911.zip -w "--departure_time 2018-09-12-07:30:00 --originsfile graphs/aus_vic_melb_20180911/SA2_origins_manual.csv --destsfile graphs/aus_vic_melb_20180911/SA2_destinations_manual.csv --outfile graphs/aus_vic_melb_20180911/SA2_SA2_ODM_repetition_test2.csv --mode_list 'WALK,TRANSIT'"
                
                There is an assumption that GTFS.zip, osm.pbf and (optionally) .tif data are stored 
                in the./graphs/project_folder directory.  
                
    -r       run Open Trip Planner (use -x too if needed)
END_HELP
}

############################################################################
# Get options
############################################################################
getOptions() {
  local OPTIND;
  while getopts ":hvd:p:t:rw:x" opt; do
    case "$opt" in
      v) VERBOSE=1 ;;
      d) PROJ_NAME=${OPTARG}; PROJ_DIR=${DIR}/graphs/${OPTARG};;
      p) OSM=${PROJ_DIR}/${OPTARG};;
      t) GTFSZIP=${PROJ_DIR}/${OPTARG};;
      r) RUN_OTP=1 ;;
      w) CALCULATE_ODM=1 ; ODM_ARGS=$OPTARG ;;
      x) BUILD_GRAPH=1 ;;
      h) usage ; exit 0 ;;
      \?) echo "Invalid option: -$OPTARG" >&2 ; usage >&2; exit 1 ;;
      :) echo "Option -$OPTARG requires an argument." >&2; exit 1 ;;
    esac
  done
  shift $((OPTIND-1))
}

############################################################################
# Build graph
############################################################################
buildGraph() {
  # check if we have the open trip planner JAR, else download it
  if [ ! -f "$OTPJAR" ]; then
    printf "\nOpen Trip Planner JAR ($OTPJAR) not found; will try to download it now ...\n"
    # check if wget is installed, else abort
    command -v wget >/dev/null 2>&1 || {
      echo >&2 "Program 'wget' not found.  Please install and try again. Aborting.";
      exit 1;
    }
    CMD="wget -O ${OTPJAR} http://maven.conveyal.com/org/opentripplanner/otp/0.19.0/otp-0.19.0-shaded.jar"
    if [ $VERBOSE -eq 1 ] ; then echo $CMD; fi ;eval $CMD
  fi

  # build graphs
  if [ ! -f "$PROJ_DIR/Graph.obj" ]; then
    printf "\nBuilding $PROJ_DIR/Graph.obj\n"
    CMD="java -Xmx3G -jar $OTPJAR --build $PROJ_DIR"
    if [ $VERBOSE -eq 1 ] ; then echo $CMD; fi; eval $CMD
  fi
}

############################################################################
# Run Open Trip Planner
############################################################################
runOTP() {
  CMD="java -Xmx3G -jar $OTPJAR --help"
  if [ $VERBOSE -eq 1 ] ; then echo $CMD; fi; eval $CMD

  # launch OTP
  CMD="java -Xmx3G -jar $OTPJAR --graphs $PROJ_DIR/.. --analyst --server --router $PROJ_NAME"
  if [ $VERBOSE -eq 1 ] ; then echo $CMD; fi; eval $CMD
}


############################################################################
# Calculate Origin Destination Matrix
############################################################################
calculateODM() {
  buildGraph

  if [ ! -f "$JYTHONJAR" ]; then
    CMD="wget -O $JYTHONJAR http://search.maven.org/remotecontent?filepath=org/python/jython-standalone/2.7.0/jython-standalone-2.7.0.jar"
    if [ $VERBOSE -eq 1 ] ; then echo $CMD; fi; eval $CMD
  fi

  CMD="java  -Duser.timezone=Australia/Melbourne -cp $OTPJAR:$JYTHONJAR:$SQLITEJAR org.python.util.jython $ODM_SCRIPT $ODM_ARGS --proj_dir $PROJ_DIR"
  echo $CMD
  if [ $VERBOSE -eq 1 ] ; then echo $CMD; fi; eval $CMD
}

############################################################################
# Main script starts here
############################################################################

OTPJAR=${DIR}/otp-0.19.0-shaded.jar
JYTHONJAR=${DIR}/jython-standalone-2.7.0.jar
SQLITEJAR=${DIR}/sqlite-jdbc-3.23.1.jar
ODM_SCRIPT=${DIR}/odm.py
getOptions "$@"

if [ $BUILD_GRAPH -eq 1 ] ; then buildGraph ; fi
if [ $CALCULATE_ODM -eq 1 ] ; then calculateODM $ODM_ARGS; fi
if [ $RUN_OTP -eq 1 ] ; then runOTP ; fi
