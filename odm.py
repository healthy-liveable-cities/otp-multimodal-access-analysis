# !/usr/bin/jython

# This Jython script is run via run-otp.should
# It assumes 
#     - OTP, Jython and Sqlite jars are acquired
#     - required input files are present and accurately specified as arguments
################################################################################################
# Example usage from Bash shell:
################################################################################################
# odm_args="--departure_time 2018-09-27-08:00:00                                               \
#           --duration_reps 2 2                                                                \
#           --max_time 7200                                                                    \
#           --max_walking_distance 500                                                         \
#           --matching one-to-many                                                             \
#           --originsfile graphs/sa1_dzn_modes_melb_2016/SA1_2016_melb_gccsa_10km_epsg4326.csv \
#           --destsfile graphs/sa1_dzn_modes_melb_2016/DZN_2016_melb_gccsa_10km_epsg4326.csv   \
#           --outdb graphs/sa1_dzn_modes_melb_2016/SA1_DZN_2016_melb_gccsa_10km.db             \
#           --outtable od_6modes_8am_10am                                                      \
#           --mode_list WALK BICYCLE CAR 'WALK,BUS' 'WALK,TRAM' 'WALK,RAIL' 'WALK,TRANSIT'     \
#           --run_once WALK BICYCLE CAR                                                        \
#           --id_names SA1_MAINCODE_2016 DZN_CODE_2016                                         \
#           --latlon_names Y X                                                                 \
#           --wideform                                                                         \
#           --proj_dir ./graphs/sa1_dzn_modes_melb_2016"
# 
# ./run-otp.sh  -d sa1_dzn_modes_melb_2016                \
#               -p melb_gccsa_2016_10000m_20180208.pbf  \
#               -t gtfs_aus_vic_melb_20180911.zip -w    \
#               "$odm_args"
###################################################################################################

import argparse, time, os.path, sys, itertools
from org.opentripplanner.scripting.api import OtpsEntryPoint
from datetime import datetime,timedelta
import sys

from java.lang import Class
from java.sql  import DriverManager, SQLException

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d-%H:%M:%S")
    except ValueError:
        msg = "Not a valid departure time: '{0}'. It should be in the format %Y-%m-%d-%H:%M ".format(s)
        raise argparse.ArgumentTypeError(msg)
          
def valid_path(arg):
    if not os.path.exists(arg):
        msg = "The path %s does not exist!" % arg
        raise argparse.ArgumentTypeError(msg)
    else:
        return arg   
        
def valid_duration_reps(arg):
    print(arg)
    if arg[0]<0:
        msg = "The duration %s cannot be negative!" % arg
        raise argparse.ArgumentTypeError(msg)
    elif arg[1]<0:
        msg = "The repeat interval %s cannot be negative!" % arg
        raise argparse.ArgumentTypeError(msg)
    elif arg[1]>arg[0]:
        msg = "The repeat interval {} cannot be smaller than the analysis duration {}!".format(args[1],args[0])
        raise argparse.ArgumentTypeError(msg)
    else:
        return arg
        
# Parse input arguments
parser = argparse.ArgumentParser(description='Generate origin destination matrix')
parser.add_argument('--departure_time',
                    help='departure time - format YYYY-MM-DD-HH:MM:SS',
                    required=True,
                    type=valid_date)
parser.add_argument('--duration_reps',
                    help='Two optional parameters defining a time duration and a repeat interval in hours.',
                    nargs=2,
                    default=[0,0],
                    type=float)                    
parser.add_argument('--proj_dir',
                    help='project directory',
                    required=True,
                    type=valid_path)
parser.add_argument('--originsfile',
                    help='path to the input csv file, which contains coordinates of origins',
                    required=True,
                    type=valid_path)
parser.add_argument('--destsfile',
                    help='path to the input csv file, which contains coordinates of destinations',
                    required=True,
                    type=valid_path)
parser.add_argument('--outdb',
                    help='path to the output sqlite database (default: traveltime_matrix)',
                    default='traveltime_matrix.db')
parser.add_argument('--outtable',
                    help='path to the output sqlite database (default: traveltime_matrix)',
                    default='traveltime_matrix')
parser.add_argument('--max_time',
                    help='maximum travel time in seconds (default: 1800)',
                    default=1800,
                    type=int)
parser.add_argument('--max_walking_distance',
                    help='maximum walking distance in meters (default: 500)',
                    default=30000,
                    type=int)
parser.add_argument('--mode_list',
                    help='Modes to travel by.  Options --pending appropriate data-- are: WALK, BICYCLE, CAR, TRAM, SUBWAY, RAIL, BUS, FERRY, CABLE_CAR, GONDOLA, FUNICULAR, TRANSIT, LEG_SWITCH, AIRPLANE (default: WALK,BUS,RAIL)',
                    nargs='*',
                    type = str,
                    default=['WALK','BUS','RAIL'])
parser.add_argument('--run_once',
                    help='Modes for which transport is only evaluated at one time point.  For example, you may be evaluating difference between on-peak and off-peak travel times, however no difference would be expected for walking or cycling, so these may be excluded (e.g. WALK BICYCLE).  Valid options are as per mod_list; the default is an empty list.',
                    nargs='*',
                    type = str,
                    default=[])
parser.add_argument('--matching',
                    help='How origins and destinations should be matched. Can be either one-to-one or one-to-many (default: one-to-many)',
                    default='one-to-many',
                    type=str)
parser.add_argument('--combinations', 
                    help='Create all combinations of supplied destination list',
                    default=False, 
                    action='store_true')
parser.add_argument('--id_names', 
                    help='Names of respective ID fields for source Origin and Destination csv files (default: GEOID GEOID)',
                    nargs='*',
                    type = str,
                    default=['GEOID','GEOID'])
parser.add_argument('--latlon_names', 
                    help='Names of latitude and longitude fields in source Origin and Destination csv fields (default: lat lon)',
                    nargs='*',
                    type = str,
                    default=['lat','lon'])
parser.add_argument('--wideform', 
                    help='Transpose data to wideform from longform main output',
                    default=False, 
                    action='store_true')
parser.add_argument('--cmd', 
                    help='The command used to call the python script may be specified; if so it is recorded to the log txt file.',
                    default=None)
args = parser.parse_args()

# Get the project name from the supplied project directory
proj_name = os.path.basename(os.path.normpath(args.proj_dir))

# db settings
DATABASE    = "{}".format(args.outdb)
JDBC_URL    = "jdbc:sqlite:%s"  % DATABASE
JDBC_DRIVER = "org.sqlite.JDBC"

TABLE_NAME      = "{}".format(args.outtable)
TABLE_DROPPER   = "drop table if exists %s;" % TABLE_NAME
TABLE_CREATOR   = "create table %s ( 'origin', 'destination', 'dep_time','mode','dist_m', 'time_mins' );" % TABLE_NAME
RECORD_INSERTER = "insert into %s values (?, ?, ?, ?, ?, ?);" % TABLE_NAME

def getConnection(jdbc_url, driverName):
    """
        Given the name of a JDBC driver class and the url to be used 
        to connect to a database, attempt to obtain a connection to 
        the database.
    """
    try:
        Class.forName(driverName).newInstance()
    except Exception, msg:
        print msg
        sys.exit(-1)
    
    try:
        dbConn = DriverManager.getConnection(jdbc_url)
    except SQLException, msg:
        print msg
        sys.exit(-1)
    
    return dbConn

def populateTable(dbConn, feedstock):
    """
        Given an open connection to a SQLite database and a list of tuples
        with the data to be inserted, insert the data into the target table.
    """
    try:
        preppedStmt = dbConn.prepareStatement(RECORD_INSERTER)
        for origin, destination, dep_time, mode, dist_m, time_mins in feedstock:
            preppedStmt.setString(1, origin)
            preppedStmt.setString(2, destination)
            preppedStmt.setString(3, dep_time)
            preppedStmt.setString(4, mode)
            preppedStmt.setInt(5, dist_m)
            preppedStmt.setDouble(6, time_mins)
            preppedStmt.addBatch()
        dbConn.setAutoCommit(False)
        preppedStmt.executeBatch()
        dbConn.setAutoCommit(True)
    except SQLException, msg:
        print msg
        return False
    
    return True

#################################################################################    

# Instantiate an OtpsEntryPoint
otp = OtpsEntryPoint.fromArgs(['--graphs', 'graphs', '--router', proj_name])

# Start timing the code
start_time = time.time()

# Get the default router
router = otp.getRouter(proj_name)

# Create a default request for a given time
req = otp.createRequest()

# set a limit to maximum travel time (seconds) 
req.setMaxTimeSec(args.max_time)

# set maximum walking distance
req.setMaxWalkDistance(args.max_walking_distance)

# Read Points of Destination - The file points.csv, drawing on defaults or specified IDs, latitude and longitude
orig_id = args.id_names[0]
dest_id = args.id_names[1]
lat = args.latlon_names[0]
lon = args.latlon_names[1]

origins = otp.loadCSVPopulation(args.originsfile, lat, lon)
dests   = otp.loadCSVPopulation(args.destsfile, lat, lon)

# Instantiate SQL connection
dbConn = getConnection(JDBC_URL, JDBC_DRIVER)
stmt = dbConn.createStatement()
try:
    stmt.executeUpdate(TABLE_DROPPER)
    stmt.executeUpdate(TABLE_CREATOR)
except SQLException, msg:
    print msg
    sys.exit(1)

# Process modes for OTP
if args.combinations is False:
  #  modes can be specified at command line --- or not
  # Default is =['WALK','BUS','RAIL'] -- as in three seperate modes;
  # To consider these as a multimodal chain, specify: 
  #       --mode_list 'WALK,BUS,RAIL'
  # To consider both together and seperately specify:
  #       --mode_list 'WALK,BUS,RAIL' WALK BUS RAIL
  # or, the equivalent
  #       --mode_list 'WALK,BUS,RAIL' 'WALK' 'BUS' 'RAIL'
  modes = args.mode_list
else:
  # Form a list of all combinations of travel modes; we'll iterate over this later
  # e.g. 'WALK,BUS,RAIL' becomes ['WALK', 'BUS', 'RAIL', 'WALK,BUS', 'WALK,RAIL', 'BUS,RAIL', 'WALK,BUS,RAIL']
  modes = [','.join(x) for x in reduce(lambda acc, x: acc + list(itertools.combinations(args.mode_list, x)), range(1, len(args.mode_list) + 1), [])]

run_once = args.run_once  


# Save the parameters used to generate the result, along with date and time of analysis
commencement = datetime.now().strftime("%Y%m%d_%H%M")
parameter_file = open(os.path.join(args.proj_dir,
                                   '{analysis}_parameters_{time}.txt'.format(analysis = os.path.basename(args.outdb),
                                                                             time = commencement)), 
                      "w")
if args.cmd is not None:
    cmd = args.cmd.replace('--','\\\n    --')
    parameter_file.write('{}\n\nCommenced at {}'.format(cmd,commencement))
else:
    parameter_file.write('{}\n\nCommenced at {}'.format('\n'.join(sys.argv[1:]),commencement))
parameter_file.close() 

# start_date = datetime.now()
start_datetime = args.departure_time
date_list = [start_datetime]
if args.duration_reps[0] > 0:
    end_datetime = start_datetime + timedelta(hours=args.duration_reps[0])
    new_datetime = start_datetime
    while new_datetime < end_datetime:
        new_datetime += timedelta(hours=args.duration_reps[1])
        date_list.append(new_datetime)

i = 0        
for dep in date_list:
    # Set departure time
    req.setDateTime(args.departure_time.year,
                    args.departure_time.month,
                    args.departure_time.day,
                    args.departure_time.hour,
                    args.departure_time.minute,
                    args.departure_time.second)
    r_dep_time    = dep.isoformat()
    # One-to-one matching
    if args.matching == 'one-to-one':
        index = 0;
        for origin, dest in itertools.izip(origins, dests):
            set_time = time.time()
            index += 1
            req.setOrigin(origin)
            r_origin = origin.getStringData(orig_id)
            print("Processing dep {}: origin {}...".format(r_dep_time,r_origin)),
            set = []
            for transport_mode in modes:
                if (transport_mode not in run_once) or (transport_mode in run_once and i == 0):
                    # define transport mode
                    req.setModes(transport_mode)
                    
                    spt = router.plan(req)
                    
                    if spt is None: 
                        # print "SPT is None"
                        continue
                    
                    # Evaluate the SPT for all points
                    result = spt.eval(dest)
                    # Add a new row of result in the CSV output
                    if result is not None:
                        if (result.getTime() is not None) and (0 <= result.getTime() <=1800) :
                            r_destination = dest.getStringData(dest_id)
                            r_mode        = '"{}"'.format(transport_mode)
                            r_dist_m      = int(result.getWalkDistance())
                            r_time_mins   = result.getTime()/60.0   
                            set.append((r_origin, r_destination, r_dep_time, r_mode, r_dist_m, r_time_mins))
            populateTable(dbConn, set)
            print("Completed in %g seconds" % (time.time() - set_time))
  
    # One-to-many matching
    if args.matching == 'one-to-many':
        all_dests = []
        for dest in dests:
            all_dests.append(dest.getStringData(dest_id))
        
        for index, origin in enumerate(origins):
            set_time = time.time()
            req.setOrigin(origin)
            r_origin      = origin.getStringData(orig_id)
            print("Processing dep {}: origin {}...".format(r_dep_time,r_origin)),
            set = []
            for transport_mode in modes:
                if (transport_mode not in run_once) or (transport_mode in run_once and i == 0):
                    # define transport mode
                    req.setModes(transport_mode)
                    
                    spt = router.plan(req)
                    
                    if spt is None: 
                        # print "SPT is None"
                        continue
                    
                    # Evaluate the SPT for all points
                    result = spt.eval(dests)
                    # Add a new row of result in the CSV output
                    for r in result:
                        if (result.getTime() is not None) and (0 <= result.getTime() <=1800) :
                            r_destination = r.getIndividual().getStringData(dest_id)
                            r_mode        = '"{}"'.format(transport_mode)
                            r_dist_m      = int(r.getWalkDistance())
                            r_time_mins   = r.getTime()/60.0   
                            set.append((r_origin, r_destination, r_dep_time, r_mode, r_dist_m, r_time_mins))
            populateTable(dbConn, set)
            print("Completed in %g seconds" % (time.time() - set_time))
    i+=1

# Close the database connection
stmt.close()
dbConn.close()    

# Stop timing the code
completion_time = datetime.now().strftime("%Y%m%d_%H%M")
duration = time.time() - start_time
parameter_file = open(os.path.join(args.proj_dir,
                                   '{analysis}_parameters_{time}.txt'.format(analysis = os.path.basename(args.outdb),
                                                                             time = commencement)), 
                      "a")
parameter_file.write('\nCompleted at {}\nDuration (hours): {}'.format(completion_time,duration))
parameter_file.close() 
print("Elapsed time was {:.2} hours".format(duration/60/60))
print("Processed OD travel estimates for modes: {}".format(modes))
