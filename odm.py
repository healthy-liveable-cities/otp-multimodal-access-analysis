# !/usr/bin/jython

# Commands to run the script
# OD matrix for departure times every half hour from 7.30 for 2 hours from SA2 origins to SA2 destinations 
# using chaining of 'WALK,BUS,RAIL' 'WALK,BUS', 'WALK,RAIL', 'WALK', 'CYCLE':
# CLASSPATH=../otp-0.19.0-shaded.jar jython -J-Xmx7G odm.py --departure_time 2018-09-12-07:30:00 --duration_reps 2 .5 --originsfile graphs/aus_vic_melb_20180911/SA2_origins_manual.csv --destsfile graphs/aus_vic_melb_20180911/SA2_destinations_manual.csv --outfile graphs/aus_vic_melb_20180911/SA2_SA2_ODM_repetition_test.csv --mode_list 'WALK,BUS,RAIL' 'WALK,BUS', 'WALK,RAIL', 'WALK', 'CYCLE'
#
# Or, more broadly using the run-top.sh wrapper s
# ./run-otp.sh  -d aus_vic_melb_20180911 -p melb_gccsa_2016_10000m_20180208.pbf -t gtfs_aus_vic_melb_20180911.zip -w "--departure_time 2018-09-12-07:30:00 --duration_reps 2 .5 --originsfile graphs/aus_vic_melb_20180911/SA2_origins_manual.csv --destsfile graphs/aus_vic_melb_20180911/SA2_destinations_manual.csv --outfile graphs/aus_vic_melb_20180911/SA2_SA2_ODM_repetition_test.csv --mode_list 'WALK,BUS,RAIL' 'WALK,BUS', 'WALK,RAIL', 'WALK', 'CYCLE'"
# Or, to generate combinations
# ./run-otp.sh  -d aus_vic_melb_20180911 -p melb_gccsa_2016_10000m_20180208.pbf -t gtfs_aus_vic_melb_20180911.zip -w "--departure_time 2018-09-12-07:30:00 --duration_reps 2 .5 --originsfile graphs/aus_vic_melb_20180911/SA2_origins_manual.csv --destsfile graphs/aus_vic_melb_20180911/SA2_destinations_manual.csv --outfile graphs/aus_vic_melb_20180911/SA2_SA2_ODM_repetition_test.csv --mode_list WALK BUS RAIL --combinations"
# Or, using default mode ('WALK,BUS,RAIL'):
# ./run-otp.sh  -d aus_vic_melb_20180911 -p melb_gccsa_2016_10000m_20180208.pbf -t gtfs_aus_vic_melb_20180911.zip -w "--departure_time 2018-09-12-07:30:00 --duration_reps 2 .5 --originsfile graphs/aus_vic_melb_20180911/SA2_origins_manual.csv --destsfile graphs/aus_vic_melb_20180911/SA2_destinations_manual.csv --outfile graphs/aus_vic_melb_20180911/SA2_SA2_ODM_repetition_test.csv"

import argparse, time, os.path, sys, itertools
from org.opentripplanner.scripting.api import OtpsEntryPoint
from datetime import datetime,timedelta

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
                    help='Two optional parameters defining a time duration and a repeat interval in hours',
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
parser.add_argument('--outfile',
                    help='path to the output csv file (default: traveltime_matrix)',
                    default='traveltime_matrix.csv')
parser.add_argument('--max_time',
                    help='maximum travel time in seconds (default: 7200)',
                    default=7200,
                    type=int)
parser.add_argument('--max_walking_distance',
                    help='maximum walking distance in meters (default: 500)',
                    default=500,
                    type=int)
parser.add_argument('--mode_list',
                    help='Modes to travel by.  Options --pending appropriate data-- are: WALK, BICYCLE, CAR, TRAM, SUBWAY, RAIL, BUS, FERRY, CABLE_CAR, GONDOLA, FUNICULAR, TRANSIT, LEG_SWITCH, AIRPLANE (default: WALK,BUS,RAIL)',
                    nargs='*',
                    type = str,
                    default=['WALK','BUS','RAIL'])
parser.add_argument('--matching',
                    help='How origins and destinations should be matched. Can be either one-to-one or one-to-many (default: one-to-many)',
                    default='one-to-many',
                    type=str)
parser.add_argument('--combinations', 
                    help='Create all combinations of supplied destination list',
                    default=False, 
                    action='store_true')
parser.add_argument('--wideform', 
                    help='Transpose data to wideform from longform main output',
                    default=False, 
                    action='store_true')
args = parser.parse_args()

# Get the project name from the supplied project directory
proj_name = os.path.basename(os.path.normpath(args.proj_dir))

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

# Read Points of Destination - The file points.csv contains the columns GEOID, X and Y.
# origins = otp.loadCSVPopulation(os.path.join(args.proj_dir,args.originsfile), 'lat', 'lon')
# dests = otp.loadCSVPopulation(os.path.join(args.proj_dir,args.destsfile), 'lat', 'lon')
origins = otp.loadCSVPopulation(args.originsfile, 'lat', 'lon')
dests = otp.loadCSVPopulation(args.destsfile, 'lat', 'lon')

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

# Create a CSV output
matrixCsv = otp.createCSVOutput()
matrixCsv.setHeader([ 'Origin', 'Destination', 'Departure_time','Transport_mode(s)','Walk_distance (meters)', 'Travel_time (seconds)' ])

# start_date = datetime.now()
start_datetime = args.departure_time
date_list = [start_datetime]
if args.duration_reps[0] > 0:
    end_datetime = start_datetime + timedelta(hours=args.duration_reps[0])
    new_datetime = start_datetime
    while new_datetime <= end_datetime:
        new_datetime += timedelta(hours=args.duration_reps[1])
        date_list.append(new_datetime)

for dep in date_list:
    # Set departure time
    req.setDateTime(args.departure_time.year,
                    args.departure_time.month,
                    args.departure_time.day,
                    args.departure_time.hour,
                    args.departure_time.minute,
                    args.departure_time.second)

    # One-to-one matching
    if args.matching == 'one-to-one':
        index = 0;
        for origin, dest in itertools.izip(origins, dests):
            index += 1
            req.setOrigin(origin)
            for transport_mode in modes:
                print("Processing {mode}: {index} {origin} to {dest}".format(index=index,origin=origin,dest=dest,mode=transport_mode))
                # define transport mode
                req.setModes(transport_mode)
                
                spt = router.plan(req)
                
                if spt is None: 
                    print "SPT is None"
                    continue
    	        
                # Evaluate the SPT for all points
                result = spt.eval(dest)
                # Add a new row of result in the CSV output
                if result is None:
                    matrixCsv.addRow([ origin.getStringData('GEOID'), dest.getStringData('GEOID'),dep.isoformat(),'"{}"'.format(transport_mode), 0 , 'OUT_OF_BOUNDS'])
                else:                                                                             
                    matrixCsv.addRow([ origin.getStringData('GEOID'), dest.getStringData('GEOID'),dep.isoformat(), '"{}"'.format(transport_mode),result.getWalkDistance() , result.getTime()/60.0])
    
    # One-to-many matching
    if args.matching == 'one-to-many':
        all_dests = []
        for dest in dests:
            all_dests.append(dest.getStringData('GEOID'))
    
        for index, origin in enumerate(origins):
            found_dests = []
            req.setOrigin(origin)
            for transport_mode in modes:
                print("Processing {mode}: {index} {origin}".format(index=index,origin=origin,mode=transport_mode))
                # define transport mode
                req.setModes(transport_mode)
                
                spt = router.plan(req)
                
                if spt is None: 
                    print "SPT is None"
                    continue
    	        
                # Evaluate the SPT for all points
                result = spt.eval(dests)
                # Add a new row of result in the CSV output
                for r in result:
                    found_dests.append(r.getIndividual().getStringData('GEOID'))
                    matrixCsv.addRow([ origin.getStringData('GEOID'),r.getIndividual().getStringData('GEOID'),dep.isoformat(),  '"{}"'.format(transport_mode), r.getWalkDistance() , r.getTime()/60.0])
                
                for dest in list(set(all_dests) - set(found_dests)):                                          
                    matrixCsv.addRow([ origin.getStringData('GEOID'),dest,dep.isoformat(),  '"{}"'.format(transport_mode), 0 , 'OUT_OF_BOUNDS'])

# Save the result
matrixCsv.save(args.outfile)
# Save the parameters used to generate the result, along with date and time of analysis
parameter_file = open(os.path.join(args.proj_dir,
                                   '{analysis}_parameters_{time}.txt'.format(analysis = os.path.basename(args.outfile),
                                                                             time = datetime.now().strftime("%Y%m%d_%H%M"))), 
                      "w")
parameter_file.write('\n'.join(sys.argv[1:]))
parameter_file.close() 

## Make wide form versions of result by walk distance and travel time seperated by mode combinations
## This assumes you have python with pandas installed!
## Pandas doesn't work in Jython, but is an easy way of munging around with transposing data; so, we do this in Python
if args.wideform is not False:
  import subprocess as sp
  sp.call('python odm_combo_wide_long.py {}'.format(args.outfile), shell=True)

# Stop timing the code
print("Elapsed time was %g seconds" % (time.time() - start_time))
print("Processed OD travel estimates for modes: {}".format(modes))
