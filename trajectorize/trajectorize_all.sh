#!/bin/bash

subreddit=$1
job_name=${subreddit}_trajectorize_all
output_file=${subreddit}_trajectorize_all.out

base_script_path="${HOME}/reddit/trajectorize"
cd $base_script_path

export SUBREDDIT=$subreddit
sbatch --job-name="${job_name}" --output="${output_file}" trajectorize_all_wrapped.sh

# To run this do something like
# ./trajectorize_all.sh bikewrench