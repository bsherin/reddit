#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel


base_path="/projects/p32275"
base_script_path="${HOME}/reddit/trajectorize"
json_path="${HOME}/reddit/trajectorize/trajectorize.json"

cd $base_script_path

python --version
echo $SUBREDDIT
python -u "scores_to_trajectories_uid.py" "$json_path" ${SUBREDDIT} ${SNAPSHOT_UID} ${base_path}
python -u "build_trajectory_report_uid.py" "$json_path" ${SUBREDDIT} ${SNAPSHOT_UID} ${base_path}