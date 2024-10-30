#!/bin/bash

subreddit=$1
job_name=${subreddit}_preprocess
output_file=${subreddit}_preprocess.out

export SUBREDDIT=$subreddit

base_script_path="${HOME}/reddit/preprocess"
cd $base_script_path

job1_id=$(sbatch --job-name="${job_name}" --output="${output_file}" preprocess_wrapped.sh | awk '{print $4}')

job_name2=${subreddit}_preprocess_exp
output_file2=${subreddit}_preprocess_exp.out
base_script_path2="${HOME}/reddit/preprocess_exp"

cd $base_script_path2
sbatch --job-name="${job_name2}" --output="${output_file2}"  --dependency=afterok:${job1_id} preprocess_exp_wrapped.sh


# To run this do something like
# ./preprocess_sequence.sh bikewrench