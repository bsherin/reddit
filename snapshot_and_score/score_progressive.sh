#!/bin/bash

subreddit=$1
unique_id=$2
months=$3

base_script_path="${HOME}/reddit/snapshot_and_score"

cd $base_script_path

export SUBREDDIT=$subreddit
export UNIQUE_ID=$unique_id
export MONTHS=$months

job_name=${subreddit}_score_progressive_${unique_id}
output_file="${HOME}/reddit/outfiles/${job_name}.out"
sbatch --job-name="${job_name}" --output="${output_file}" score_progressive_wrapped.sh

# To run this do something like
# ./score_progressive.sh bikewrench 82f7e 6