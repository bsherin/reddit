#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --job-name=CSVTokToParquetMagic
#SBATCH --output=CSVTokToParquetMagic
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

python --version
python ~/reddit/scripts/CSVTokenizedToDFParquetMultig_script.py --json ~/reddit/json_and_sh/CSVTokenizedToDFParquetMultig_magic_json.json
