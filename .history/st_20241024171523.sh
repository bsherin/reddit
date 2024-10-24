#!/bin/bash

subreddit=$1
job_name=${subreddit}_sscore_trajectorize



base_script_path="${HOME}/reddit"
start_seed=1
end_seed=5

cd $base_script_path

export SUBREDDIT=$subreddit
for seed in $(seq $start_seed $end_seed); do
    echo "Launching batch script with seed value: $seed"
    export SEED=$seed
    base_unique_d=$(date +%s%N | md5sum | head -c 5)
    unique_id="${base_unique_d}_${seed}"
    output_file=${subreddit}_sscore_trajectorize_${unique_id}.out
    echo "output_file is $output_file"
    sbatch --job-name="${job_name}" --output="${output_file}" snapshot_score_trajectorize_wrapped.sh
done
# To run this do something like
# ./snapshot_score_trajectorize.sh bikewrench