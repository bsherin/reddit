#!/bin/bash

base_script_path="${HOME}/reddit/characterize"
cd $base_script_path

for subreddit in "$@"; do
    job_name=${subreddit}_characterize
    output_file="${HOME}/reddit/outfiles/${job_name}.out"
    export SUBREDDIT=$subreddit
    sbatch --job-name="${job_name}" --output="${output_file}" characterize_wrapped.sh
done

# To run this do something like
# ./characterize.sh bikewrench science