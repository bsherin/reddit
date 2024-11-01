#!/bin/bash

subreddit=$1

base_script_path="${HOME}/reddit/average"
cd $base_script_path

full_path="/projects/p32275/${subreddit}"

export FOLDER_OF_MODELS="${full_path}"
export MIN_POSTS=2000

export USE_EXP="true"
job_name=${subreddit}_avg_true
outfile="${HOME}/reddit/outfiles/${job_name}.out"
sbatch --job-name="${job_name}" --output="${outfile}" average_trajectories_smart_wrapped.sh

export USE_EXP="false"
job_name=${subreddit}_avg_false
outfile="${HOME}/reddit/outfiles/${job_name}.out"
sbatch --job-name="${job_name}" --output="${outfile}" average_trajectories_smart_wrapped.sh

job_name="${subreddit}_explore"
base_script_path="${HOME}/reddit/explore_experience"
output_file="${HOME}/reddit/outfiles/${job_name}.out"
cd "$base_script_path"
export SUBREDDIT="$subreddit"
sbatch --job-name="${job_name}" --output="${output_file}" explore_exp_wrapped.sh

# To run this do something like
# ./avg_and_exp.sh bikewrench