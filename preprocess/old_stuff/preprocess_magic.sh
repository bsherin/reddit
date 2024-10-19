#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --job-name=magic_combo
#SBATCH --output=magic_combo
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

python --version
python ~/reddit/scripts_combo/SubRedditToCsv_script.py --json ~/reddit/scripts_combo/magic_combo.json
python ~/reddit/scripts_combo/CSVPrep_script.py --json ~/reddit/scripts_combo/magic_combo.json
python ~/reddit/scripts_combo/CSVPureToTokenizedMultig_script.py --json ~/reddit/scripts_combo/magic_combo.json
python ~/reddit/scripts_combo/CSVTokenizedToDFParquetMultig_script.py --json ~/reddit/scripts_combo/magic_combo.json
