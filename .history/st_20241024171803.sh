#!/bin/bash

subreddit=$1
unique_id=$2
job_name=${subreddit}_score_trajectorize_${unique_id}

base_script_path="${HOME}/reddit"
start_seed=1
end_seed=5

cd $base_script_path

export SUBREDDIT=$subreddit
export UNIQUE_ID=$unique_id
output_file=${subreddit}_sscore_trajectorize_${unique_id}.out
echo "output_file is $output_file"
sbatch --job-name="${job_name}" --output="${output_file}" score_trajectorize_wrapped.sh
# To run this do something like
# ./snapshot_score_trajectorize.sh bikewrench 9ax35