#!/bin/bash

results_pickle=$1
fn=$2
fv=$3
fk

job_name=${re_report}_${fn}_${fv}

base_script_path="${HOME}/reddit/average"
cd $base_script_path

export RESULTS_PICKLE="${results_pickle}"
export FN="${fn}"
export fv="${fv}"
sbatch --job-name="${job_name}" --output="${job_name}.out" average_trajectories_wrapped.sh

# To run this do something like
# ./avg.sh StarWars/exp_models 2000