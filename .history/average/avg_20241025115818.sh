#!/bin/bash

subreddit=$1
job_name=${subreddit}_characterize
output_file=${subreddit}_characterize.out

base_script_path="${HOME}/reddit/characterize"
cd $base_script_path

export SUBREDDIT=$subreddit
sbatch --job-name="${job_name}" --output="${output_file}" characterize_wrapped.sh

# To run this do something like
# ./characterize.sh bikewrench