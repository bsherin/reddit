#!/bin/bash
#SBATCH --account=p32275
#SBATCH --partition=normal
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=10
#SBATCH --time=10:00:00
#SBATCH --mem-per-cpu=5G
#SBATCH --mail-type=ALL
#SBATCH --mail-user=bsherin@u.northwestern.edu

# Desired kernel name
TARGET_KERNEL="first-kernel"

# Check the currently activated Conda environment
if [[ "$CONDA_DEFAULT_ENV" != "$TARGET_KERNEL" ]]; then
    # If the desired kernel is not activated, load modules and activate it
    module purge all
    module load python-anaconda3
    eval "$(conda shell.bash hook)"
    conda activate "$TARGET_KERNEL"
else
    echo "The target kernel '$TARGET_KERNEL' is already activated."
fi

base_path="/projects/p32275"
base_script_path="${HOME}/reddit/preprocess"
json_path="${HOME}/reddit/preprocess/preprocess.json"

cd $base_script_path

python --version
python -u "${base_script_path}/zsts_to_post_csv.py" "$json_path" ${SUBREDDIT} ${base_path}
python -u "${base_script_path}/zsts_to_user_data.py" "$json_path" ${SUBREDDIT} ${base_path}
python -u "${base_script_path}/clean_and_add_seconds.py" "$json_path" ${SUBREDDIT} ${base_path}
python -u "${base_script_path}/tokenize_cleaned_csv_new2.py" "$json_path" ${SUBREDDIT} ${base_path}
## python -u "${base_script_path}/eval_and_convert_to_parquet.py" "$json_path" ${SUBREDDIT} ${base_path}
python -u "${base_script_path}/add_true_date_info.py" "$json_path" ${SUBREDDIT} ${base_path}

base_script_path="${HOME}/reddit/preprocess_exp"
json_path="${HOME}/reddit/preprocess_exp/preprocess_exp.json"

cd $base_script_path

python -u "zsts_to_exp_df.py" "$json_path" ${SUBREDDIT} ${base_path}
python -u "add_seconds.py" "$json_path" ${SUBREDDIT} ${base_path}
python -u "add_true_date_info.py" "$json_path" ${SUBREDDIT} ${base_path}

base_script_path="${HOME}/reddit/characterize"
json_path="${HOME}/reddit/characterize/characterize.json"

cd $base_script_path

python -u "characterize.py" "$json_path" ${SUBREDDIT} ${base_path}
