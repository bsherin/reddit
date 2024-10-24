
import pandas as pd
import sys
import os
snaphot_folder = sys.argv[1]
param_df = pd.read_csv(f"{snaphot_folder}/parameters.txt", sep=":\t", engine="python", names=["key", "value"], index_col="key")
is_exp = "threshold_in_days" in param_df.index
seed = param_df.loc["seed"].value
uid = param_df.loc["uid"].value
subreddit = param_df.loc["subreddit"].value

if is_exp:
    new_folder_name = f"{subreddit}_snapshots_exp_{uid}"
else:
    new_folder_name = f"{subreddit}_snapshots_{uid}"

os.rename(snaphot_folder, new_folder_name)