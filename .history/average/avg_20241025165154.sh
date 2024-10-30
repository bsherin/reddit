#!/bin/bash
job_name=$1
folder_of_models=$2

base_script_path="${HOME}/reddit/average"
cd $base_script_path

full_path="/projects/p32275/${folder_of_models}"

export FOLDER_OF_MODELS="${full_path}"
sbatch --job-name="${job_name}" --output="${job_name}.out" average_trajectories_wrapped.sh

# To run this do something like
# ./avg.sh star_wars_job StarWars/exp_models 2000