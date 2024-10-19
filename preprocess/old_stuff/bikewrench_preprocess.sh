#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --job-name=bikewrench_combo
#SBATCH --output=bikewrench_combo.out
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel

subreddit=bikewrench
base_script_path="${HOME}/reddit/preprocess"
json_path="${HOME}/reddit/scripts_combo/${subreddit}_preprocess.json"

python --version
python "${base_script_path}/zsts_to_post_csv.py" "$json_path"
python "${base_script_path}/zsts_to_user_data.py" "$json_path"
python "${base_script_path}/clean_and_add_seconds.py" "$json_path"
python "${base_script_path}/tokenize_cleaned_csv.py" "$json_path"
python "${base_script_path}/eval_and_convert_to_parquet.py" "$json_path"
python "${base_script_path}/add_true_date_info.py" "$json_path"
