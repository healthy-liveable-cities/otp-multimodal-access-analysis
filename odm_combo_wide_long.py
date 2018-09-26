# This script takes the output from odm_combinations.py 
# (a jython script for running OpenTripPlanner analyses across combinations of travel modes)
# and transforms it to wide format

# If running this on Ubuntu / Unix4Win you may need to 
# sudo apt-get install python-pip
# sudo pip install numpy
# sudo pip install pandas

import pandas as pd
import os
import sys

if len(sys.argv) < 2:
  print("Hey, there's no output filename specified!  This program expects this as an argument in order to run")
  print("(For example, you could run: python odm_combo_wide_long.py SA2_SA2_ODM.all_mode_combinations.csv ")
else:
  infile  = sys.argv[1]
  outdir = os.path.dirname(infile)
  # read csv back in as Pandas dataframe (df)
  df = pd.read_csv(infile )
  combos = df['Transport_mode(s)'].unique()
  # make wide using walk distance
  df_w_dist = df[['Origin', 'Destination','Walk_distance (meters)','Transport_mode(s)']].set_index(['Origin', 'Destination', 'Transport_mode(s)']).unstack('Transport_mode(s)')
  
  # make wide using travel time
  df_t_time = df[['Origin', 'Destination', 'Travel_time (seconds)','Transport_mode(s)']].set_index(['Origin', 'Destination', 'Transport_mode(s)']).unstack('Transport_mode(s)')
  
  # Reset indices so they appear as regular columns
  df_w_dist.columns = df_w_dist.columns.droplevel()
  df_w_dist.reset_index(level=[0,1], inplace=True)
  df_t_time.columns = df_t_time.columns.droplevel()
  df_t_time.reset_index(level=[0,1], inplace=True)
  
  # output to csv, with original travel mode combo order
  stub = os.path.splitext(os.path.basename(infile ))[0]
  df_w_dist[['Origin','Destination']+list(combos)].to_csv(os.path.join(outdir,'{}_walk_dist_m.csv'.format(stub)))
  df_t_time[['Origin','Destination']+list(combos)].to_csv(os.path.join(outdir,'{}_travel_time_mins.csv'.format(stub))) 
  
