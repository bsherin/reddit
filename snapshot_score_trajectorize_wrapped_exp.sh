#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

base_unique_id=$(date +%s%N | md5sum | head -c 5)
unique_id="${base_unique_id}_exp_${RUN_NUMBER}"
echo "Extended Unique ID: $unique_id"

base_path="/projects/p32275"
base_script_path="${HOME}/reddit/snapshot_and_score"
json_path="${HOME}/reddit/snapshot_and_score/snapshot_and_score_exp_sampling.json"

cd $base_script_path

python --version
echo $SUBREDDIT
python -u "create_snapshot_models_exp_sampling.py" "$json_path" ${SUBREDDIT} ${base_path} "$unique_id" ${RUN_NUMBER}
python -u "score_posts_from_snapshots_uid.py" "$json_path" ${SUBREDDIT} ${base_path} "$unique_id"

base_script_path="${HOME}/reddit/trajectorize"
json_path="${HOME}/reddit/trajectorize/trajectorize.json"

cd $base_script_path

python --version
echo $SUBREDDIT
python -u "scores_to_trajectories_uid.py" "$json_path" ${SUBREDDIT}  "$unique_id" ${base_path}
python -u "build_trajectory_report_uid.py" "$json_path" ${SUBREDDIT} "$unique_id" ${base_path}