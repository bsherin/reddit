### This script is used to generate the trajectory dataframes for a given snapshot
### It the exp_df, user_df, and scored dataframe for the snapshot
### It writes the trajectory dataframes to the snapshot folder
### The key info is written to trajectory_key_info.json

print("starting")
import pickle
import json
import sys
import pickle
import os
import re
import pandas as pd
from pandas import Timedelta
import pyarrow.parquet as pq
import json

initialized = False
db_timer = None



CORPUS_END_YEAR = 2022
CORPUS_END_MONTH = 12
END_BUFFER = 12

CORPUS_END = pd.Timestamp(year=CORPUS_END_YEAR, month=CORPUS_END_MONTH, day=31)
end_buffer_td = pd.Timedelta(weeks=(END_BUFFER * 4))

buffered_corpus_end = CORPUS_END - end_buffer_td

from utilities import flatten, ds, save_to_json

y_axis_labels = {
    "num_phases": "phase",
    "raw_post_count": "posts",
    "time": "weeks",
    "experience": "pseudo weeks",
    "ntokens_bins": "ntokens"
}

stage_kinds = ["num_phases", "ntokens_bins", "raw_post_count", "time", "experience"]

def vectorized_stages_scores(df, user_df):
    good_users = user_df[user_df["last_post"] <= buffered_corpus_end]
    good_user_list = good_users.index.tolist()
    df = df[df['author'].isin(good_user_list)]
    posts_per_phase = df['total_user_posts'] / Tile.num_phases
    base_stage = (df['post_number'] / posts_per_phase).astype(int) + 1
    remaining_fraction = (posts_per_phase - df['post_number'] % posts_per_phase)

    scores = df[Tile.uid]

    # Handling the conditional logic for remaining_fraction >= 1
    base_fraction = remaining_fraction.clip(upper=1)
    base_score = base_fraction * scores
    if Tile.have_ntokens:
        base_ntokens = base_fraction * df["ntokens"]
    else:
        base_ntokens = 0
    base_fraction = base_fraction.where(base_score != 0, 0)
    # Calculation of next fraction, stage, and score with updated conditions
    next_fraction = (1 - base_fraction).where(base_fraction < 1, 0)
    next_stage = (base_stage + 1).where(base_fraction < 1, -99)
    next_score = next_fraction * scores
    if Tile.have_ntokens:
        next_ntokens = next_fraction * df["ntokens"]
    else:
        next_ntokens = 0
    next_fraction = next_fraction.where(next_score != 0, 0)

    result_df = pd.DataFrame({
        'first_stage': base_stage,
        'first_fraction': base_fraction,
        'first_score': base_score,
        "first_ntokens": base_ntokens,
        'second_stage': next_stage,
        'second_fraction': next_fraction,
        'second_score': next_score,
        "second_ntokens": next_ntokens
    })
    return result_df

def vectorized_posts_scores(df):
    base_stage = (df['post_number'] / Tile.post_bin_size).astype(int) + 1
    base_score = df[Tile.uid]
    if Tile.have_ntokens:
        base_ntokens = df["ntokens"]
    else:
        base_ntokens = 0
    base_fraction = (base_score != 0).astype(int)
    next_fraction = 0
    next_stage = -99
    next_score = 0
    next_ntokens = 0
    result_df = pd.DataFrame({
        'first_stage': base_stage,
        'first_fraction': base_fraction,
        'first_score': base_score,
        "first_ntokens": base_ntokens,
        'second_stage': next_stage,
        'second_fraction': next_fraction,
        'second_score': next_score,
        "second_ntokens": next_ntokens
    })
    return result_df

def vectorized_ntokens_scores(df):
    base_score = df[Tile.uid]
    if Tile.have_ntokens:
        base_stage = (df['ntokens'] / Tile.ntokens_bin_size).astype(int) + 1
        base_ntokens = df["ntokens"]
    else:
        base_stage = 0
        base_ntokens = 0
    base_fraction = (base_score != 0).astype(int)
    next_fraction = 0
    next_stage = -99
    next_score = 0
    next_ntokens = 0
    result_df = pd.DataFrame({
        'first_stage': base_stage,
        'first_fraction': base_fraction,
        'first_score': base_score,
        "first_ntokens": base_ntokens,
        'second_stage': next_stage,
        'second_fraction': next_fraction,
        'second_score': next_score,
        "second_ntokens": next_ntokens
    })
    return result_df

def vectorized_experience_scores(df):
    base_stage = (df['experience'] / Tile.experience_bin_size).astype(int) + 1
    base_score = df[Tile.uid]
    if Tile.have_ntokens:
        base_ntokens = df["ntokens"]
    else:
        base_ntokens = 0
    base_fraction = (base_score != 0).astype(int)
    next_fraction = 0
    next_stage = -99
    next_score = 0
    next_ntokens = 0
    result_df = pd.DataFrame({
        'first_stage': base_stage,
        'first_fraction': base_fraction,
        'first_score': base_score,
        "first_ntokens": base_ntokens,
        'second_stage': next_stage,
        'second_fraction': next_fraction,
        'second_score': next_score,
        "second_ntokens": next_ntokens
    })
    return result_df

def vectorized_time_scores(df):
    period_in_secs = Tile.period_in_weeks * 7 * 86400
    base_stage = (df['user_seconds'] / period_in_secs).astype(int) + 1
    base_score = df[Tile.uid]
    if Tile.have_ntokens:
        base_ntokens = df["ntokens"]
    else:
        base_ntokens = 0
    base_fraction = (base_score != 0).astype(int)
    next_fraction = 0
    next_stage = -99
    next_score = 0
    next_ntokens = 0
    result_df = pd.DataFrame({
        'first_stage': base_stage,
        'first_fraction': base_fraction,
        'first_score': base_score,
        "first_ntokens": base_ntokens,
        'second_stage': next_stage,
        'second_fraction': next_fraction,
        'second_score': next_score,
        "second_ntokens": next_ntokens
    })
    return result_df

month_list = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]

def month_number(month_name):
    if month_name in month_list:
        return 1 + month_list.index(month_name)
    return int(month_name)

def month_name(month_number):
    return month_list[month_number - 1]

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)


print("done with globals")
class ScoresToTrajectoriesExpAutoK():
    def __init__(self, jsonfile, subreddit, snapshot_uid, base_path):
        import textwrap
        with open(jsonfile, 'r') as file:
            config = json.load(file)
        self.subreddit_name = subreddit
        self.working_directory = f"{base_path}/{self.subreddit_name}"
        self.uid = snapshot_uid
        self.snapshot_folder = f"{base_path}/{subreddit}/{subreddit}_snapshots_{self.uid}"
        self.user_df_pfile = f"{self.working_directory}/{self.subreddit_name}_user_data.parquet"
        self.exp_df_pfile =  f"{self.working_directory}/{self.subreddit_name}_df_exp_true.parquet"

        self.remove_exp_duplicates = config["remove_exp_duplicates"] if "remove_exp_duplicates" in config else False
        self.num_phases = config["num_phases"] if "num_phases" in config else 20
        self.post_bin_size = config["post_bin_size"] if "post_bin_size" in config else 10
        self.period_in_weeks = config["period_in_weeks"] if "period_in_weeks" in config else 4
        self.min_instances = config["min_instances"] if "min_instances" in config else 50
        self.experience_bin_size = config["experience_bin_size"] if "experience_bin_size" in config else 28
        self.ntokens_bin_size = config["ntokens_bin_size"] if "ntokens_bin_size" in config else 5
        self.minimum_user_posts = config["minimum_user_posts"] if "minimum_user_posts" in config else 50

        self.option_names = ["snapshot_folder", "user_df_pfile", "exp_df_pfile", "remove_exp_duplicates", "force_fill_experience", "num_phases", "post_bin_size", "period_in_weeks", "min_instances", "experience_bin_size", "ntokens_bin_size", "minimum_user_posts", "output_file"]
        return

    def pull_param_vals(self):
        param_df = pd.read_csv(f"{self.snapshot_folder}/parameters.txt", sep=":\t", engine="python", names=["key", "value"], index_col="key")
        keys = param_df.index.tolist()
        for key in keys:
            setattr(self, key, param_df.loc[key].value)
        if type(self.uid) is not str:
            param_df = pd.read_csv(f"{self.snapshot_folder}/parameters.txt", sep=":\t", engine="python", names=["key", "value"], index_col="key",  dtype={'value': str})
            self.uid = param_df.loc["uid"].value
        return
    
    def set_key_info(self):
        self.key_info = {
            "model": self.uid,
            "truncate": self.truncate_text,
            "start": self.start_date.strftime('%Y-%m-%d'),
            "end": self.end_date.strftime('%Y-%m-%d'),
            "min_user_posts": self.minimum_user_posts,
            "nusers": self.n_good_users,
            "num_phases": self.num_phases,
            "post_bin": self.post_bin_size,
            "time_bin_weeks": self.period_in_weeks,
            "k": self.k,
            "exp_bin_size": self.experience_bin_size,
            "ntokens_bin_size": self.ntokens_bin_size,
            "min_instances": self.min_instances,
        }
        if self.truncate_text == "True":
            self.key_info["max_len"] = self.max_len
        
        if hasattr(self, "max_vocab_size"):
            self.key_info["vocab"] = self.max_vocab_size
    
    def get_good_users(self, user_df):    
        good_users = user_df
        if self.minimum_user_posts > 1:
            good_users["total_posts"] = good_users.apply(lambda row: row["top_level_comments"] + row["submissions"], 1)
            good_users = good_users[good_users["top_level_comments"] >= self.minimum_user_posts]
    
        # good_users = good_users[good_users["first_post"] >= self.start_date]
        # good_users = good_users[good_users["last_post"] <= self.end_date]
        return good_users.index.tolist()
    
    def process_stage_kind(self, stage_kind, score_df, user_df):
        try:
            stage_scale_factors = {
                "num_phases": 1,
                "ntokens_bins": self.ntokens_bin_size,
                "raw_post_count": self.post_bin_size,
                "time": self.period_in_weeks,
                "experience": int(self.experience_bin_size) / 7
            }
            max_phase = None
            if stage_kind == "num_phases":
                resultant_columns = vectorized_stages_scores(score_df, user_df)
                max_phase = self.num_phases
            else:
                if stage_kind == "ntokens_bins":
                    print("got ntokens_bins")
                    resultant_columns = vectorized_ntokens_scores(score_df)
                elif stage_kind== "raw_post_count":
                    resultant_columns = vectorized_posts_scores(score_df)
                elif stage_kind == "experience":
                    if "experience" not in score_df.columns:
                        return
                    resultant_columns = vectorized_experience_scores(score_df)
                else:
                    resultant_columns = vectorized_time_scores(score_df)
                vcs = resultant_columns["first_stage"].value_counts().tolist()
                for n, c in enumerate(vcs):
                    if c < self.min_instances:
                        max_phase = n # note we want the prior n + 1, which happens to be n
                        break
                if max_phase is None:
                    max_phase = n
            tscore_df = score_df.join(resultant_columns)
            result_dicts = []
        
            for stage in range(1, max_phase + 1):
                fdf = tscore_df[tscore_df["first_stage"] == stage]
                ndf = tscore_df[tscore_df["second_stage"] == stage]
                total_score = fdf["first_score"].sum() + ndf["second_score"].sum()
                if self.have_ntokens:
                    total_ntokens = fdf["first_ntokens"].sum() + ndf["second_ntokens"].sum()
                else:
                    total_ntokens = 0
                denom = fdf["first_fraction"].sum() + ndf["second_fraction"].sum()
                result_dicts.append({
                    y_axis_labels[stage_kind]: stage * stage_scale_factors[stage_kind],
                    "score": total_score / denom,
                    "nposts": denom,
                    "avg_ntokens": total_ntokens / denom,
                    # "first_stage_rows": len(fdf),
                    # "second_stage_rows": len(ndf)
                })

            trajdf = pd.DataFrame(result_dicts)
            trajdf.to_parquet(f"{self.snapshot_folder}/{stage_kind}_trajectory_df.parquet")
            return
        except Exception as e:
            print(f"Error in process_stage_kind {stage_kind}: {e}")
            return

    def render_content(self):

        ds("Reading exp_df")
        exp_df = load_pickle_or_parquet(self.exp_df_pfile)
        self.k = exp_df["dt"].mean()
        
        
        ds("Pulling snapshot params")
        self.pull_param_vals()
        
        # self.pull_param_vals will create these attributes on self
        # 'uid', 'df_pkl', 'user_df_pkl', 'output_location', 'output_folder_name', 'overwrite_allowed', '
        # abort_on_month_failure', 'min_users_per_month', 'min_posts_per_month', 'users_per_month', 'posts_per_user', 
        # 'start_month', 'start_year', 'end_month', 'end_year', 'prune_before_start', 'prune_after_end', 
        # 'min_user_posts', 'max_vocab_size', 'max_discount, truncate_text, max_len
        
        if not hasattr(self, "truncate_text"):
            self.truncate_text = False
        
        self.start_month = month_number(self.start_month)
        self.end_month = month_number(self.end_month)
        self.end_year = int(self.end_year)
        self.start_year = int(self.start_year)
        
        self.uid = str(self.uid)
        
        ds("Reading score df")
        
        self.score_df_pfile = f"{self.snapshot_folder}/{self.subreddit_name}_scored_{self.uid}.parquet"
        
        score_df = load_pickle_or_parquet(self.score_df_pfile)
        
        with open(f"{self.snapshot_folder}/used_posts.pkl","rb") as f:
            all_used_posts = flatten(pickle.load(f))
        
        score_df = score_df[~score_df.index.isin(all_used_posts)]
        
        ds("Reading user_df")
        user_df = load_pickle_or_parquet(self.user_df_pfile)
        
        ds("Pruning users")
        
        edate = pd.Timestamp(year=self.end_year, month=self.end_month, day=1)
        self.end_date = edate.to_period('M').to_timestamp(how='end')
        self.start_date = pd.Timestamp(year=self.start_year, month=self.start_month, day=1)
        good_user_list = self.get_good_users(user_df)
        self.n_good_users = len(good_user_list)
        score_df = score_df[score_df['author'].isin(good_user_list)]
        score_df = score_df[score_df[self.uid] != -999]
        
        # if -999 in score_df[self.uid].tolist():
        #     bad_df = score_df[score_df[self.uid] == -999]
        #     print("bad_df with {} rows".format(len(bad_df)))
        #     return 
        
        score_df["experience"] = exp_df["experience"]
        
        ds("Filling stage columns")
        self.have_ntokens = "ntokens" in score_df.columns
        
        for stage_kind in stage_kinds:
            self.process_stage_kind(stage_kind, score_df, user_df)

        self.set_key_info()
        save_to_json(self.key_info, f"{self.snapshot_folder}/trajectory_key_info.json")

if __name__ == '__main__':
    print("starting")
    # jsonfile, subreddit, snapshot_uid, base_path)
    Tile = ScoresToTrajectoriesExpAutoK(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    Tile.render_content()