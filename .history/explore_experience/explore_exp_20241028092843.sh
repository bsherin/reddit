#!/bin/bash

subreddit=$1
job_name=${subreddit}_explore


base_script_path="${HOME}/reddit/explore_experience"
output_file=${HOME}/reddit/outfiles/${job_name}.out

cd $base_script_path

export SUBREDDIT=$subreddit
sbatch --job-name="${job_name}" --output="${output_file}" explore_exp_wrapped.sh

# To run this do something like
# ./explore_exp.sh bikewrench