#!/bin/bash

subreddit=$1
snapshot_uid=$2
job_name=${subreddit}_trajectorize
output_file=${subreddit}_trajectorize.out

base_script_path="${HOME}/reddit/trajectorize"
cd $base_script_path

export SUBREDDIT=$subreddit
export SNAPSHOT_UID=$snapshot_uid
sbatch --job-name="${job_name}" --output="${output_file}" trajectorize_wrapped.sh

# To run this do something like
# ./trajectorize.sh bikewrench 9ccf3