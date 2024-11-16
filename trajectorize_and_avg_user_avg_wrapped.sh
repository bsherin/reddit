#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=1:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel


base_path="/projects/p32275"
base_script_path="${HOME}/reddit/trajectorize"
json_path="${HOME}/reddit/trajectorize/trajectorize_user_avg.json"

full_path="/projects/p32275/${SUBREDDIT}"

cd $base_script_path

python --version
echo $SUBREDDIT
python -u "trajectorize_user_avg_all.py" "$json_path" ${SUBREDDIT} ${base_path}

base_script_path="${HOME}/reddit/average"
cd $base_script_path
python -u "average_trajectories_smart_user_avg.py" ${full_path} "true" 2000 

python -u "average_trajectories_smart_user_avg.py" ${full_path} "false" 2000