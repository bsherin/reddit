### This script is used to generate the trajectory dataframes for a given snapshot
### It the exp_df, user_df, and scored dataframe for the snapshot
### It writes the trajectory dataframes to the snapshot folder
### Each trajectory dataframe has the following columns:
### num_phases, ntokens_bins, raw_post_count, [x-axis col], experience

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

x_axis_labels = {
    "num_phases_user_avg": "phase",
    "raw_post_count_uvg": "posts",
}

stage_kinds = ["num_phases_user_avg", "raw_post_count_uvg"]

month_list = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]

def month_number(month_name):
    if month_name in month_list:
        return 1 + month_list.index(month_name)
    return int(month_name)

def month_name(month_number):
    return month_list[month_number - 1]

def load_pickle_or_parquet(path):
    ext = os.path.splitext(path)[1]
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)


print("done with globals")
class TrajectorizeUserAvg():
    def __init__(self, jsonfile, subreddit, snapshot_uid, base_path):
        import textwrap
        with open(jsonfile, 'r') as file:
            config = json.load(file)
        self.subreddit_name = subreddit
        self.working_directory = f"{base_path}/{self.subreddit_name}"
        self.uid = snapshot_uid
        self.snapshot_folder = f"{base_path}/{subreddit}/{subreddit}_snapshots_{self.uid}"
        self.user_df_pfile = f"{self.working_directory}/{self.subreddit_name}_user_data.parquet"

        self.num_phases = config["num_phases"] if "num_phases" in config else 20
        self.minimum_user_posts = config["minimum_user_posts"] if "minimum_user_posts" in config else 50
        self.nposts = config["num_posts"] if "num_posts" in config else 50
        self.remove_high_posters = config["remove_high_posters"] if "remove_high_posters" in config else False
        self.high_post_limit = config["high_post_limit"] if "high_post_limit" in config else 20000

        if self.remove_high_posters:
            self.output_folder = f"{self.snapshot_folder}/trajectory_data_hpl_user_avg_{self.high_post_limit}"
        else:
            self.output_folder = f"{self.snapshot_folder}/trajectory_data_user_avg"
        if not os.path.isdir(self.output_folder):
            os.mkdir(self.output_folder)

    def pull_param_vals(self):
        param_df = pd.read_csv(f"{self.snapshot_folder}/parameters.txt", sep=":\t", engine="python", names=["key", "value"], index_col="key")
        keys = param_df.index.tolist()
        for key in keys:
            setattr(self, key, param_df.loc[key].value)
        if type(self.uid) is not str:
            param_df = pd.read_csv(f"{self.snapshot_folder}/parameters.txt", sep=":\t", engine="python", names=["key", "value"], index_col="key",  dtype={'value': str})
            self.uid = param_df.loc["uid"].value
        return
    
    def vectorized_stages_scores(self, df, user_df):
        good_users = user_df[user_df["last_post"] <= buffered_corpus_end]
        good_user_list = good_users.index.tolist()
        df = df[df['author'].isin(good_user_list)]
        posts_per_phase = df['total_user_posts'] / self.num_phases
        base_stage = (df['post_number'] / posts_per_phase).astype(int) + 1
        remaining_fraction = (posts_per_phase - df['post_number'] % posts_per_phase)

        scores = df[self.uid]

        # Handling the conditional logic for remaining_fraction >= 1
        base_fraction = remaining_fraction.clip(upper=1)
        base_score = base_fraction * scores
        base_fraction = base_fraction.where(base_score != 0, 0)
        # Calculation of next fraction, stage, and score with updated conditions
        next_fraction = (1 - base_fraction).where(base_fraction < 1, 0)
        next_stage = (base_stage + 1).where(base_fraction < 1, -99)
        next_score = next_fraction * scores
        next_fraction = next_fraction.where(next_score != 0, 0)

        result_df = pd.DataFrame({
        'first_stage': base_stage,
            'first_fraction': base_fraction,
            'first_score': base_score,
            'second_stage': next_stage,
            'second_fraction': next_fraction,
            'second_score': next_score,
        })
        return result_df

    def vectorized_posts_scores(self, df):
        base_stage = df['post_number']
        base_score = df[self.uid]

        base_fraction = (base_score != 0).astype(int)
        next_fraction = 0
        next_stage = -99
        next_score = 0
        result_df = pd.DataFrame({
            'first_stage': base_stage,
            'first_fraction': base_fraction,
            'first_score': base_score,
            'second_stage': next_stage,
            'second_fraction': next_fraction,
            'second_score': next_score,
        })
        return result_df
    
    def set_key_info(self):
        self.key_info = {
            "model": self.uid,
            "truncate": self.truncate_text,
            "start": self.start_date.strftime('%Y-%m-%d'),
            "end": self.end_date.strftime('%Y-%m-%d'),
            "min_user_posts": self.minimum_user_posts,
            "nusers": self.n_good_users,
            "num_phases": self.num_phases,
            "num_posts": self.nposts
        }
        if self.truncate_text == "True":
            self.key_info["max_len"] = self.max_len
        
        if hasattr(self, "max_vocab_size"):
            self.key_info["vocab"] = self.max_vocab_size
    
    def get_good_users(self, user_df):    
        good_users = user_df
        if self.minimum_user_posts > 1 or self.remove_high_posters:
            good_users["total_posts"] = good_users.apply(lambda row: row["top_level_comments"] + row["submissions"], 1)
            
        if self.minimum_user_posts > 1:
            good_users = good_users[good_users["total_posts"] >= self.minimum_user_posts]
    
        if self.remove_high_posters:
            good_users = good_users[good_users["total_posts"] <= self.high_post_limit]
        return good_users.index.tolist()
    
    def process_stage_kind(self, stage_kind, score_df, user_df):
        ds(f"Processing stage kind: {stage_kind}")
        stage_scale_factors = {
            "num_phases_user_avg": 1,
            "raw_post_count_uvg": 1,
        }
        max_phase = None
        if stage_kind == "num_phases_user_avg":
            pscore_df = score_df
            resultant_columns = self.vectorized_stages_scores(score_df, user_df)
            max_phase = self.num_phases
            stage_name = f"num_phases_user_avg_ {self.num_phases}"
        else:  # stage_kind == "raw_post_count_uvg"
            pscore_df = score_df[score_df["post_number"] <= self.nposts]
            resultant_columns = self.vectorized_posts_scores(pscore_df)
            max_phase = self.nposts
            stage_name = f"raw_post_count_uvg_{self.nposts}"
        tscore_df = pscore_df.join(resultant_columns)
        result_dicts = []
    
        for stage in range(1, max_phase + 1):
            # Filter the DataFrame for the given stage
            fdf = tscore_df[tscore_df["first_stage"] == stage]
            ndf = tscore_df[tscore_df["second_stage"] == stage]

            # Group by author and compute the total score and denominator for each author
            fdf_author = fdf.groupby("author").agg(
                total_score=("first_score", "sum"),
                total_fraction=("first_fraction", "sum")
            )
            ndf_author = ndf.groupby("author").agg(
                total_score=("second_score", "sum"),
                total_fraction=("second_fraction", "sum")
            )

            # Combine the two DataFrames for each author
            author_totals = fdf_author.add(ndf_author, fill_value=0)

            # Compute the score for each author
            author_totals["author_score"] = author_totals["total_score"] / author_totals["total_fraction"]

            # Average the author scores
            avg_score = author_totals["author_score"].mean()
            result_dicts.append({
                x_axis_labels[stage_kind]: stage * stage_scale_factors[stage_kind],
                "score": avg_score
            })

        trajdf = pd.DataFrame(result_dicts)
        trajdf.to_parquet(f"{self.output_folder}/{stage_name}_trajectory_df.parquet")
        return

    def render_content(self):
        
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
        
        for stage_kind in stage_kinds:
            self.process_stage_kind(stage_kind, score_df, user_df)

        self.set_key_info()
        save_to_json(self.key_info, f"{self.output_folder}/trajectory_key_info.json")

if __name__ == '__main__':
    print("starting")
    # jsonfile, subreddit, snapshot_uid, base_path)
    Tile = TrajectorizeUserAvg(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    Tile.render_content()