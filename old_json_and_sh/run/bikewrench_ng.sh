#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=00:10:00
#SBATCH --mem-per-cpu=5G
#SBATCH --job-name=bikewrench_ngram
#SBATCH --output=bikewrench_out
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

python --version
python ngram_user_trajectories_script.py --json bikewrench_trajectories_json.json
