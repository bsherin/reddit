#!/bin/bash

subreddit=$1
job_name=${subreddit}_sscore_trajectorize_exp

unique_id=$(date +%s | md5sum | cut -d' ' -f1 | cut -c1-3)
output_file=${subreddit}_sscore_trajectorize_${unique_id}.out

base_script_path="${HOME}/reddit"
cd $base_script_path

export SUBREDDIT=$subreddit
sbatch --job-name="${job_name}" --output="${output_file}" snapshot_score_trajectorize_wrapped_exp.sh

# To run this do something like
# ./sst_exp.sh bikewrench