#!/bin/bash
echo "starting"
s
ubreddit=$1
type=$2
fn=$3
fv=$4
fk=$5

echo "Subreddit: ${subreddit}"
if [[ $type == "reg" ]]; then
    results_pickle="/projects/p32275/${subreddit}/avg/${subreddit}_avg_results.pkl"
else
    results_pickle="/projects/p32275/${subreddit}/exp_avg/${subreddit}_avg_exp_results.pkl"
fi
echo "Results pickle: ${results_pickle}"
job_name=${re_report}_${fn}_${fv}

base_script_path="${HOME}/reddit/average"
cd $base_script_path

export RESULTS_PICKLE="${results_pickle}"
export FN="${fn}"
export FV="${fv}"
export FK="${fk}"
sbatch --job-name="${job_name}" --output="${job_name}.out" re_report_wrapped.sh

# To run this do something like
# ./re_report.sh science exp nposts 2000 ">="