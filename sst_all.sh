#!/bin/bash

subreddit=$1

base_script_path="${HOME}/reddit"
start_run_number=1
end_run_number=15

cd $base_script_path

export SUBREDDIT=$subreddit
for run_number in $(seq $start_run_number $end_run_number); do
    echo "Launching batch script with run_number value: $run_number"
    export RUN_NUMBER=$run_number
    base_unique_d=$(date +%s%N | md5sum | head -c 5)
    unique_id="${base_unique_d}_${run_number}"
    job_name=${subreddit}_sscore_trajectorize_${unique_id}
    output_file="${HOME}/reddit/outfiles/${job_name}.out"
    echo "output_file is $output_file"
    sbatch --job-name="${job_name}" --output="${output_file}" snapshot_score_trajectorize_wrapped.sh
done

start_run_number=1
end_run_number=15

for run_number in $(seq $start_run_number $end_run_number); do
    export RUN_NUMBER=$run_number
    echo "Launching exp batch script with run_number value: $run_number"
    base_unique_d=$(date +%s%N | md5sum | head -c 5)
    unique_id="${base_unique_d}_exp_${run_number}"
    job_name=${subreddit}_sscore_trajectorize_${unique_id}
    output_file="${HOME}/reddit/outfiles/${job_name}.out"
    echo "output_file is $output_file"
    sbatch --job-name="${job_name}" --output="${output_file}" snapshot_score_trajectorize_wrapped_exp.sh
done

# To run this do something like
# ./sst_all.sh bikewrench