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
# Do debug you can run from bash interactively in the otp directory the following:
# DIR="."
# OTPJAR=${DIR}/otp-0.19.0-shaded.jar
# JYTHONJAR=${DIR}/jython-standalone-2.7.0.jar
# SQLITEJAR=${DIR}/sqlite-jdbc-3.23.1.jar
#
# java  -Duser.timezone=Australia/Melbourne -cp $OTPJAR:$JYTHONJAR:$SQLITEJAR org.python.util.jython
#  
# When running code interactively, don't enter the  parser.parse_args() function - it will crash the script
# The following alternate variable definitions may be of use:
# 
# DATABASE = "graphs/sa1_dzn_region10_2019/region10_gccsa_SA1_DZN_2016_vic.db"
# originsfile = "graphs/sa1_dzn_region10_2019/sa1_2016_network_snapped_pwc_region10.csv"
# destsfile = "graphs/sa1_dzn_region10_2019/dzn_2016_network_snapped_centroids_region10.csv"
# TABLE_NAME = "od_4modes_7_45am"
# id_names = ['SA1_MAINCO','DZN_CODE_2016']
# latlon_names =['Y','X']

import argparse, time, os.path, sys, itertools
from org.opentripplanner.scripting.api import OtpsEntryPoint
from datetime import datetime,timedelta
import sys
import csv

from java.lang import Class
from java.sql  import DriverManager, SQLException
from com.ziclix.python.sql import zxJDBC

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

def createTable(table,values = " 'origin', 'destination', 'dep_time','mode','dist_m', 'time_mins' "):
    """
        Return string to create a database table pending given context (results, origins or destinations)
    """
    if table == "origins":
        TABLE_CREATOR   = "create table if not exists origins_{} ({});".format(TABLE_NAME,values)
    if table == "destinations":
        TABLE_CREATOR   = "create table if not exists destinations_{} ({});".format(TABLE_NAME,values)
    if table == "results":
        TABLE_CREATOR   = "create table if not exists {} ({});".format(TABLE_NAME,values)
    return(TABLE_CREATOR)

def insertRows(table,values="?,?,?,?,?,?"):
    """
        Return string to insert rows to a database table pending given context (results, origins or destinations)
    """
    if table == "origins":
        RECORD_INSERTER   = "insert into origins_{} values ({});".format(TABLE_NAME,values)
    if table == "destinations":
        RECORD_INSERTER   = "insert into destinations_{} values ({});".format(TABLE_NAME,values)
    if table == "results":
        RECORD_INSERTER   = "insert into {} values ({});".format(TABLE_NAME,values)
    return(RECORD_INSERTER)    

def getConnection(JDBC_URL, JDBC_DRIVER, sql_zxJDBC=True):
    """
        Given the name of a JDBC driver class and the url to be used 
        to connect to a database, attempt to obtain a connection to 
        the database.
    """
    try:
        Class.forName(JDBC_DRIVER).newInstance()
    except Exception, msg:
        print msg
        sys.exit(-1)
    
    if sql_zxJDBC == True:
        try:
            # no user/password combo needed here, hence the None, None
            dbConn = zxJDBC.connect(JDBC_URL, None, None, JDBC_DRIVER)
        except zxJDBC.DatabaseError, msg:
            print msg
            sys.exit(-1)
    else:
        try:
            dbConn = DriverManager.getConnection(JDBC_URL)
        except SQLException, msg:
            print msg
            sys.exit(-1)
    return dbConn

def populateTable(dbConn, feedstock, sql_zxJDBC = False):
    """
        Given an open connection to a SQLite database and a list of tuples
        with the data to be inserted, insert the data into the target table.
    """
    try:
        preppedStmt = dbConn.prepareStatement(insertRows('results'))
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

# Instantiate zxJDBC SQL connection
dbConn = getConnection(JDBC_URL,JDBC_DRIVER, True)
cursor = dbConn.cursor()

try:
    cursor.execute(createTable("results"))
except SQLException, msg:
    print msg
    sys.exit(1)

with open(os.path.abspath('./{}'.format(args.originsfile)), 'rb') as f:
    reader = csv.reader(f)
    origin_list = map(tuple, reader)

with open(os.path.abspath('./{}'.format(args.destsfile)), 'rb') as f:
    reader = csv.reader(f)
    dests_list = map(tuple, reader)

try:    
    # copy origins to db
    cursor.execute("drop table if exists origins_{};".format(TABLE_NAME))
    cursor.execute(createTable(table = "origins",
                               values = "'Y', 'X', 'fid', 'SA1_MAINCO', 'SA1_7DIGIT', 'COMPOUND_ID'"))    
    cursor.executemany(insertRows("origins",','.join(['?' for x in range(0,len(origin_list[0]))])), 
                       origin_list[1:])
    dbConn.commit()
    # copy dests to db
    cursor.execute("drop table if exists destinations_{};".format(TABLE_NAME))
    cursor.execute(createTable(table = "destinations",
                               values = "'Y', 'X', 'fid', 'DZN_CODE_2016', 'COMPOUND_ID'")) 
    cursor.executemany(insertRows("destinations",','.join(['?' for x in range(0,len(dests_list[0]))])), 
                       dests_list[1:])
    dbConn.commit()   
except SQLException, msg:
    print msg
    sys.exit(1)

# SNIPPETS FOR DEBUGGING
# cursor.execute("SELECT * FROM {result};".format(result=TABLE_NAME))
# for row in cursor.fetchall():
    # print(row)
    
# Delete all records with largest ID
# Assuming records are processed sequentially by id, if the process has crashed
# the safest way to ensure all results are processed are to discard the potentially
# incomplate previous transaction set (larget id) and recommence from there.
cursor.execute('''
    DELETE FROM {result} 
    WHERE origin = (SELECT origin FROM {result} ORDER BY origin DESC LIMIT 1);
    '''.format(result=TABLE_NAME))
dbConn.commit()
cursor.execute('''DROP TABLE IF EXISTS origins_updated''')
dbConn.commit()
cursor.execute('''CREATE TABLE origins_updated AS 
                SELECT * FROM origins_{result} 
                WHERE "{id}" > COALESCE((SELECT origin FROM {result} ORDER BY origin DESC LIMIT 1),'');
                '''.format(result = TABLE_NAME,
                           id = args.id_names[0]))
dbConn.commit()
    
cursor.execute('''
    SELECT "{id}",
           "{lat}",
           "{lon}"
    FROM origins_updated
    '''.format(id = args.id_names[0],
               lat = args.latlon_names[0],
               lon = args.latlon_names[1]))
rows = cursor.fetchall()

updated_csv = '{}_updated{}'.format(*os.path.splitext(args.originsfile))
try:
    os.remove(updated_csv)
except OSError:
    pass
    
with open(updated_csv, 'w') as f:
    updated_origins = csv.writer(f)
    updated_origins.writerow((args.id_names[0],args.latlon_names[0],args.latlon_names[1]))
    updated_origins.writerows(rows)
    
# Close the zxJDBC connection
cursor.close()
dbConn.close()

# open Xenial connection
dbConn = getConnection(JDBC_URL, JDBC_DRIVER, sql_zxJDBC = False)
stmt = dbConn.createStatement()

# Read Points of Destination - The file points.csv, drawing on defaults or specified IDs, latitude and longitude
orig_id = args.id_names[0]
dest_id = args.id_names[1]
lat = args.latlon_names[0]
lon = args.latlon_names[1]

origins = otp.loadCSVPopulation(updated_csv, lat, lon)
dests   = otp.loadCSVPopulation(args.destsfile, lat, lon)


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
                        if (result.getTime() is not None) and (0 <= result.getTime() <=args.max_time) :
                            r_destination = dest.getStringData(dest_id)
                            r_mode        = '"{}"'.format(transport_mode)
                            r_dist_m      = int(0 if result.getWalkDistance() is None else result.getWalkDistance())
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
                    results = spt.eval(dests)
                    # Add a new row of result in the CSV output
                    for result in results:
                        if (result.getTime() is not None) and (0 <= result.getTime() <=args.max_time) :
                            r_destination = result.getIndividual().getStringData(dest_id)
                            r_mode        = '"{}"'.format(transport_mode)
                            r_dist_m      = int(0 if result.getWalkDistance() is None else result.getWalkDistance())
                            r_time_mins   = result.getTime()/60.0   
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
