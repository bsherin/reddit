#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --job-name=magicTCG5000_3_ixze3wl7
#SBATCH --output=magicTCG5000_3_ixze3wl7_out
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

python --version
python ~/reddit/scripts/ScorePostsFromSnapshots_script.py --json ~/reddit/json_and_sh/magicTCG5000_3_ixze3wl7.json
