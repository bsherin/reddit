#!/bin/bash
output_file=$1
folder_of_models=$2

projects_path="/projects/p32275/"

base_script_path="${HOME}/reddit/average"
cd $base_script_path

export FOLDER_OF_MODELS="${projects_path}/${folder_of_models}"
sbatch --job-name="${job_name}" --output="${output_file}" average_trajectories_wrapped.sh

# To run this do something like
# ./avg.sh outfile StarWars/exp_models