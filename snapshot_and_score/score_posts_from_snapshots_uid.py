### The script reads the {subreddit}_df_true dataframe and the snapshots, and scores the posts
### The script saves the scored dataframe to {subreddit}_scored_{uid}.parquet
### The script reads the parameters from {subreddit}_snapshots_{uid}/parameters.txt
### The saved dataframe has the following columns:
### author, post_id, seconds, subreddit, total_user_posts, post_number, true_date, experience, uid

print("starting score_posts_from_snapshots.py")
import pickle
import json
import pickle
import os, sys
import pandas as pd
from nltk.util import bigrams
from katz_class import KatzBigramLM
from typing import *


kb_model = None
truncate_text = None
max_len = None

month_list = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]

def month_number(month_name):
    return 1 + month_list.index(month_name)

def month_name(month_number):
    return month_list[month_number - 1]

def score_function(txt):
    # if truncate_text:
    #     return kb_model.entropy(list(bigrams(txt[:max_len])))
    return kb_model.entropy(list(bigrams(txt)))

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)

def ds(text):
    print(text)
    return

print("done with globals")
params = []
class ScorePostsFromSnapshots():
    def __init__(self, jsonfile, subreddit, base_path, uid):
        self.uid = uid
        self.subreddit_name = subreddit
        self.working_directory = f"{base_path}/{self.subreddit_name}"

        with open(jsonfile, 'r') as file:
            config = json.load(file)
        for param in params:
            if param in config:
                setattr(self, param, config[param])
            else:
                setattr(self, param, None)

        self.text_df_file = f"{self.working_directory}/{self.subreddit_name}_df_true.parquet"
        self.snapshot_folder = f"{self.working_directory}/{self.subreddit_name}_snapshots_{self.uid}"
        self.output_path = f"{self.snapshot_folder}/{self.subreddit_name}_scored_{self.uid}.parquet"
        return

    def display_status(self, text):
        print(text)

    def pull_param_vals(self):
        param_df = pd.read_csv(f"{self.snapshot_folder}/parameters.txt", sep=":\t", names=["key", "value"], index_col="key")
        keys = param_df.index.tolist()
        for key in keys:
            setattr(self, key, param_df.loc[key].value)
        return

    def render_content(self):
        ds("Getting snapshot params")
        global kb_model
        global truncate_text
        global max_len
        self.pull_param_vals()
        truncate_text = self.truncate_text
        max_len = int(self.max_len)
        ds("Reading text df")
        text_df = load_pickle_or_parquet(self.text_df_file)
        if "post_id" in text_df.columns:
            text_df.set_index('post_id', inplace=True)
        ds("Removing text_df duplicates")
        text_df = text_df[~text_df.index.duplicated(keep='first')]
        ds("Reading score df")

        text_df[self.uid] = -999
        smonth_num = int(self.start_month)
        emonth_num = int(self.end_month)
        self.start_year = int(self.start_year)
        self.end_year = int(self.end_year)
        for year in range(self.start_year, self.end_year + 1):
            smonth = smonth_num if year == self.start_year else 1
            emonth = emonth_num if year == self.end_year else 12
            
            for month in range(smonth, emonth + 1):
                ds(f"Processing year {year} month {month}")
                month_df = text_df[(text_df['true_date'].dt.year == year) & (text_df['true_date'].dt.month == month)]
                with open(f"{self.snapshot_folder}/snapshots/{month_name(month)}-{year}", "rb") as f:
                    snapshot_dict = pickle.load(f)
                kb_model = KatzBigramLM(50, .9)
                kb_model.__setstate__(snapshot_dict["lm_dict"])
                used_posts = snapshot_dict["post_ids"]
                month_df = month_df[~month_df.index.isin(used_posts)]
                results = month_df['text'].apply(score_function)
                text_df.loc[results.index, self.uid] = results
        
        ds("writing the file")        
        text_df.drop(columns=['text'], inplace=True)
        text_df.to_parquet(self.output_path)

if __name__ == '__main__':
    print("starting")
    Tile = ScorePostsFromSnapshots(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    Tile.render_content()