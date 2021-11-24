# Analysis 20190913

for i in "$@"
do
    region="region${i}"
    echo -e "\n${region}"
    case $i in
    "10"|"07")
      tz="Australia/Victoria"
      ;;
    "04")
      tz="Australia/Canberra"
      ;;
    "02")
      tz="Australia/NSW"
      ;;
    "12")
      tz="Australia/Darwin"
      ;;
    "01"|"03"|"05"|"06")
      tz="Australia/Queensland"
      ;;
    "11")
      tz="Australia/Adelaide"
      ;;
    "08"|"09")
      tz="Australia/Tasmania"
      ;;
    "13")
      tz="Australia/Perth"
      ;;
    esac
    
    odm_args="--departure_time 2019-10-16-07:45:00                                                         \
              --max_time 10800                                                                             \
              --max_walking_distance 100000                                                                \
              --matching one-to-many                                                                       \
              --originsfile graphs/sa1_dzn_${region}_2019/sa1_2016_network_snapped_pwc_${region}.csv       \
              --destsfile graphs/sa1_dzn_${region}_2019/dzn_2016_network_snapped_centroids_${region}.csv   \
              --outdb graphs/sa1_dzn_${region}_2019/sa1_dzn_${region}_2019_0745_max_3hrs.db                \
              --outtable od_modes_0745                                                                    \
              --mode_list WALK BICYCLE CAR 'WALK,TRANSIT'                                                  \
              --run_once WALK BICYCLE CAR                                                                  \
              --id_names SA1_MAINCO DZN_CODE_2016                                                          \
              --latlon_names Y X                                                                           \
              --wideform                                                                                   \
              --proj_dir ./graphs//sa1_dzn_${region}_2019"
    
    ./run-otp.sh  -d sa1_dzn_${region}_2019 \
                  -p 30minute_cities_${i}.osm \
                  -w "$odm_args" \
                  -t "$tz"
done


for i in "$@"
do
    region="region${i}"
    echo -e "\n${region}"
    case $i in
    "10"|"07")
      tz="Australia/Victoria"
      ;;
    "04")
      tz="Australia/Canberra"
      ;;
    "02")
      tz="Australia/NSW"
      ;;
    "12")
      tz="Australia/Darwin"
      ;;
    "01"|"03"|"05"|"06")
      tz="Australia/Queensland"
      ;;
    "11")
      tz="Australia/Adelaide"
      ;;
    "08"|"09")
      tz="Australia/Tasmania"
      ;;
    "13")
      tz="Australia/Perth"
      ;;
    esac
    
    odm_args="--departure_time 2019-10-16-10:45:00                                                         \
              --max_time 10800                                                                             \
              --max_walking_distance 100000                                                                \
              --matching one-to-many                                                                       \
              --originsfile graphs/sa1_dzn_${region}_2019/sa1_2016_network_snapped_pwc_${region}.csv       \
              --destsfile graphs/sa1_dzn_${region}_2019/dzn_2016_network_snapped_centroids_${region}.csv   \
              --outdb graphs/sa1_dzn_${region}_2019/sa1_dzn_${region}_2019_1045_max_3hrs_transit_only.db   \
              --outtable od_modes_1045                                                                    \
              --mode_list 'WALK,TRANSIT'                                                                   \
              --id_names SA1_MAINCO DZN_CODE_2016                                                          \
              --latlon_names Y X                                                                           \
              --wideform                                                                                   \
              --proj_dir ./graphs//sa1_dzn_${region}_2019"
    
    ./run-otp.sh  -d sa1_dzn_${region}_2019 \
                  -p 30minute_cities_${i}.osm \
                  -w "$odm_args" \
                  -t "$tz"
done
