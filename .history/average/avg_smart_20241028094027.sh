#!/bin/bash

folder_of_models=$1
use_exp=$2
min_posts=$3

job_name=${folder_of_models}_avg_${use_exp}
outfile="${HOME}/reddit/outfiles/${job_name}.out"

base_script_path="${HOME}/reddit/average"
cd $base_script_path

full_path="/projects/p32275/${folder_of_models}"

export FOLDER_OF_MODELS="${full_path}"
export USE_EXP="${use_exp}"
export MIN_POSTS="${min_posts}"
sbatch --job-name="${job_name}" --output="${outfile}" average_trajectories_smart_wrapped.sh

# To run this do something like
# ./avg.sh StarWars true 2000