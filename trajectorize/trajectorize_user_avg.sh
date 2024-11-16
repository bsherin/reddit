#!/bin/bash

subreddit=$1
snapshot_uid=$2
job_name=${subreddit}_trajectorize_user_avg_${snapshot_uid}
output_file="${HOME}/reddit/outfiles/${job_name}.out"

base_script_path="${HOME}/reddit/trajectorize"
cd $base_script_path

export SUBREDDIT=$subreddit
export SNAPSHOT_UID=$snapshot_uid
sbatch --job-name="${job_name}" --output="${output_file}" trajectorize_user_avg_wrapped.sh

# To run this do something like
# ./trajectorize_user_avg.sh Minecraft 2b197_exp_4