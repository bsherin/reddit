#!/bin/bash

subreddit=$1
job_name=${subreddit}_trajectorize_all_user_avg
output_file="${HOME}/reddit/outfiles/${job_name}.out"

export SUBREDDIT=$subreddit

sbatch --job-name="${job_name}" --output="${output_file}" trajectorize_and_avg_user_avg_wrapped.sh
# To run this do something like
# ./trajectorize_and_avg_user_avg.sh StarWars