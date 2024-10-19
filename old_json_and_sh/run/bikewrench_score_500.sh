#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=0:30:00
#SBATCH --mem-per-cpu=5G
#SBATCH --job-name=bikewrench_score
#SBATCH --output=bikewrench_score_500_out
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

python --version
python ~/reddit/scripts/ScorePostsFromSnapshots_script.py --json ~/reddit/json_and_sh/bikewrench_score_500.json
