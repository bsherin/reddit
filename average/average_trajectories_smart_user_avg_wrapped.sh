#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=00:10:00
#SBATCH --mem-per-cpu=5G
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

base_script_path="${HOME}/reddit/average"

cd $base_script_path

python --version
echo $SUBREDDIT
python -u "average_trajectories_smart_user_avg.py" ${FOLDER_OF_MODELS} ${USE_EXP} ${MIN_POSTS}