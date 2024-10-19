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
base_script_path="${HOME}/reddit/characterize"
json_path="${HOME}/reddit/characterize/characterize.json"

cd $base_script_path

python --version
echo $SUBREDDIT
python -u "characterize.py" "$json_path" ${SUBREDDIT} ${base_path}