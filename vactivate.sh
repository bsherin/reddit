#!/bin/bash
module purge all
module load python-anaconda3
eval "$(conda shell.bash hook)"
source activate first-kernel
