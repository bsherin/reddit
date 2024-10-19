#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=nomral
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=1-:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

unique_id=$(date +%s | md5sum | cut -d' ' -f1)

base_path="/projects/p32275"
base_script_path="${HOME}/reddit/snapshot_and_score"
json_path="${HOME}/reddit/snapshot_and_score/snapshot_and_score_exp_sampling.json"

python --version
echo $SUBREDDIT
python -u "${base_script_path}/create_snapshot_models_exp_sampling.py" "$json_path" ${SUBREDDIT} ${base_path} "$unique_id" ${SEED}
python -u "${base_script_path}/score_posts_from_snapshots.py" "$json_path" ${SUBREDDIT} ${base_path} "$unique_id"