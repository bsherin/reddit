#!/bin/bash

folder_of_models=$1
min_posts_reg=$2
min_posts_exp=$3


base_script_path="${HOME}/reddit/average"
cd $base_script_path

full_path="/projects/p32275/${folder_of_models}"

export FOLDER_OF_MODELS="${full_path}"



export USE_EXP="true"
job_name=${folder_of_models}_avg_true
outfile="${HOME}/reddit/outfiles/${job_name}.out"
export MIN_POSTS="${min_posts_reg}"
sbatch --job-name="${job_name}" --output="${outfile}" average_trajectories_smart_wrapped.sh

export USE_EXP="false"
job_name=${folder_of_models}_avg_false
outfile="${HOME}/reddit/outfiles/${job_name}.out"
export MIN_POSTS="${min_posts_exp}"
sbatch --job-name="${job_name}" --output="${outfile}" average_trajectories_smart_wrapped.sh

# To run this do something like
# ./avg_smart.sh StarWars 2000 1000