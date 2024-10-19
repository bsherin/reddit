#!/bin/bash

subreddit=$1
job_name=${subreddit}_preprocess_exp
output_file=${subreddit}_preprocess_exp.out

base_script_path="${HOME}/reddit/preprocess_exp"
cd $base_script_path

export SUBREDDIT=$subreddit
sbatch --job-name="${job_name}" --output="${output_file}" preprocess_exp_wrapped.sh

# To run this do something like
# ./preprocess_exp.sh bikewrench