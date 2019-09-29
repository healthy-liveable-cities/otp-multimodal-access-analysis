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
    -d       Specify project directory (req'd); files are assumed to be located here.  
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
    
There is an assumption that GTFS.zip, osm.pbf and (optionally) .tif data are stored 
in the./graphs/project_folder directory.  
                
Here is an example of usage at the Bash shell prompt, first storing odm.py args in a variable 
odm_args, and then executing:

odm_args="--departure_time 2018-09-27-08:00:00                                               \\
          --duration_reps 2 2                                                                \\
          --max_time 7200                                                                    \\
          --max_walking_distance 500                                                         \\
          --matching one-to-many                                                             \\
          --originsfile graphs/sa1_dzn_modes_melb_2016/SA1_2016_melb_gccsa_10km_epsg4326.csv \\
          --destsfile graphs/sa1_dzn_modes_melb_2016/DZN_2016_melb_gccsa_10km_epsg4326.csv   \\
          --outdb graphs/sa1_dzn_modes_melb_2016/SA1_DZN_2016_melb_gccsa_10km.db             \\
          --outtable od_6modes_8am_10am                                                      \\
          --mode_list WALK BICYCLE CAR 'WALK,BUS' 'WALK,TRAM' 'WALK,RAIL' 'WALK,TRANSIT'     \\
          --run_once WALK BICYCLE CAR                                                        \\
          --id_names SA1_MAINCODE_2016 DZN_CODE_2016                                         \\
          --latlon_names Y X                                                                 \\
          --wideform                                                                         \\
          --proj_dir ./graphs/sa1_dzn_modes_melb_2016"

./run-otp.sh  -d sa1_dzn_modes_melb_2016              \\
              -p melb_gccsa_2016_10000m_20180208.pbf  \\
              -t gtfs_aus_vic_melb_20180911.zip -w    \\
              "\$odm_args"          

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
    CMD="java -Xmx4G -jar $OTPJAR --build $PROJ_DIR"
    if [ $VERBOSE -eq 1 ] ; then echo $CMD; fi; eval $CMD
  fi
}

############################################################################
# Run Open Trip Planner
############################################################################
runOTP() {
  CMD="java -Xmx4G -jar $OTPJAR --help"
  if [ $VERBOSE -eq 1 ] ; then echo $CMD; fi; eval $CMD

  # launch OTP
  CMD="java -Xmx4G -jar $OTPJAR --graphs $PROJ_DIR/.. --analyst --server --router $PROJ_NAME"
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
  CMD="$CMD --cmd '''$CMD'''"
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
