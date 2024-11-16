#!/bin/bash

subreddit=$1
hpl=$2
job_name=${subreddit}_trajectorize_all
output_file=${subreddit}_trajectorize_all.out

export SUBREDDIT=$subreddit
export HPL=$hpl

sbatch --job-name="${job_name}" --output="${output_file}" trajectorize_and_avg_wrapped.sh
# To run this do something like
# ./trajectorize_and_avg.sh StarWars 10000