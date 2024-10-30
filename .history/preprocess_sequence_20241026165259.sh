#!/bin/bash

subreddit=$1
job_name=${subreddit}_preprocess
output_file=${subreddit}_preprocess.out

export SUBREDDIT=$subreddit
sbatch --job-name="${job_name}" --output="${output_file}" preprocess_wrapped.sh

# To run this do something like
# ./preprocess.sh bikewrench