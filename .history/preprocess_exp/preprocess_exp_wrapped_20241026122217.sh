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
base_script_path="${HOME}/reddit/preprocess_exp"
json_path="${HOME}/reddit/preprocess_exp/preprocess_exp.json"

cd $base_script_path

python --version
python "zsts_to_exp_df.py" "$json_path" ${SUBREDDIT} ${base_path}
python "add_seconds.py" "$json_path" ${SUBREDDIT} ${base_path}
python "add_true_date_info.py" "$json_path" ${SUBREDDIT} ${base_path}
