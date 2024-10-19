#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=00:20:00
#SBATCH --mem-per-cpu=5G
#SBATCH --job-name=${BASE_NAME}
#SBATCH --output=${BASE_NAME}.out
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

python --version
python "ngram_model_tester_base_sample_script.py" --json "${BASE_NAME}.json"
# Run with something like sbatch --export=BASE_NAME=ngram_model_tester_base_magicTCG ngram_tester.sh