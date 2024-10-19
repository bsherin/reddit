#!/bin/bash

subreddit=$1
job_name=${subreddit}_snapshot_and_score_exp
output_file=${subreddit}_snapshot_and_score_exp.out

base_script_path="${HOME}/reddit/snapshot_and_score"
cd $base_script_path

export SUBREDDIT=$subreddit
sbatch --job-name="${job_name}" --output="${output_file}" --seed=2 snapshot_and_score_wrapped_exp.sh

start_seed=2# 
end_seed=10

# Loop over the seed values
for seed in $(seq $start_seed $end_seed); do
    # Print the seed value for logging/debugging
    echo "Launching batch script with seed value: $seed"
    
    # Submit the SLURM batch script with the seed as an argument
    sbatch --export=ALL,SEED=$seed your_slurm_script.sh
    sbatch --job-name="${job_name}" --output="${output_file}" --seed=$seed snapshot_and_score_wrapped_exp.sh
done

# To run this do something like
# ./snapshot_and_score.sh bikewrench