#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --job-name=bikewrench_snapshot_and_score
#SBATCH --output=bikewrench_snapshot_and_score.out
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

unique_id=$(date +%s | md5sum | cut -d' ' -f1)

subreddit=bikewrench
base_script_path="${HOME}/reddit/snapshot_and_score"
json_path="${HOME}/reddit/snapshot_and_score/${subreddit}_snapshot_and_score.json"

python --version
python "${base_script_path}/create_snapshot_models.py" "$json_path" "$unique_id"
python "${base_script_path}/score_posts_from_snapshots.py" "$json_path" "$unique_id"