#!/bin/bash

subreddit=$1
job_name=${subreddit}_explore
output_file=${job_name}.out

base_script_path="${HOME}/reddit/explore_experience"
cd $base_script_path

export SUBREDDIT=$subreddit
sbatch --job-name="${job_name}" --output="${output_file}" explore_exp_wrapped.sh

# To run this do something like
# ./explore_exp.sh bikewrench 9ccf3