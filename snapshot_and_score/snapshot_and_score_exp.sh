#!/bin/bash

subreddit=$1
job_name=${subreddit}_snapshot_and_score_exp
output_file=${subreddit}_snapshot_and_score_exp.out

base_script_path="${HOME}/reddit/snapshot_and_score"
cd $base_script_path

export SUBREDDIT=$subreddit
export SEED=1
sbatch --job-name="${job_name}" --output="${output_file}" snapshot_and_score_wrapped_exp.sh

# To run this do something like
# ./snapshot_and_score.sh bikewrench