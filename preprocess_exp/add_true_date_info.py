### This script adds the true date of a post to the dataframe, and fills in the experience column.
### The dataframe is saved to {subreddit_name}_df_exp_true.parquet
### The experience parameters are saved to {subreddit_name}_exp_params.json
### The dataframe has the following columns:
### author, post_id, seconds, subreddit, total_user_posts, post_number, true_date, experience


print("starting add_true_date_info.py")
import json
import sys
import os
import pandas as pd
import math
import numpy as np

from datetime import datetime

first_date = None


def ds(txt):
    Tile.display_status(Tile.status_stub + txt)
    return

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)


def delta_experience(dt, k):
    if np.isnan(dt):
        return 0
    return k * (1 - math.exp(-1 * dt / k))
    
def fill_experience(exp_df, remove_exp_duplicates=False):
    if "post_id" in exp_df.columns:
        exp_df.set_index("post_id", inplace=True)
    if remove_exp_duplicates:
        exp_df = exp_df[~exp_df.index.duplicated(keep='first')]
    exp_df = exp_df.copy()
    exp_df.sort_values(by=["author", "true_date"], inplace=True)
    exp_df['dt'] = exp_df.groupby('author')['true_date'].diff().dt.total_seconds() / 86400
    k = exp_df["dt"].mean()
    print(f"got k = {k}")
    exp_df['experience_delta'] = exp_df['dt'].apply(lambda x: delta_experience(x, k))
    exp_df['experience'] = exp_df.groupby('author')['experience_delta'].cumsum()
    exp_df.drop(columns=['experience_delta'], inplace=True)
    return exp_df, k

def save_to_json(struc, path):
    with open(path, "w") as f:
        json.dump(struc, f)

print("done with globals")
params = ["working_directory", "subreddit_name",]
class LabelTrueDates():
    def __init__(self, jsonfile, subreddit, base_path):
        with open(jsonfile, 'r') as file:
            config = json.load(file)

        for param in params:
            if param in config:
                setattr(self, param, config[param])
            else:
                setattr(self, param, None)

        self.subreddit_name = subreddit
        self.working_directory = f"{base_path}/{self.subreddit_name}"
        self.user_df_path = f"{self.working_directory}/{self.subreddit_name}_user_data.parquet"
        self.df_path = f"{self.working_directory}/{self.subreddit_name}_df_exp_seconds.parquet" 
        self.output_path = f"{self.working_directory}/{self.subreddit_name}_df_exp_true.parquet"
        self.json_path = f"{self.working_directory}/{self.subreddit_name}_exp_params.json"
        return

    def display_status(self, text):
        print(text)

    def html_table(self, text):
        print(text)

    def get_parameters(self):
        plist = []
        for opt_name in self.option_names:
            plist.append({"name": opt_name, "value": getattr(self, opt_name)})
        return plist

    def render_content(self):
        global first_date
        
        self.status_stub = ""
        ds("reading")
    
        
        df = load_pickle_or_parquet(self.df_path)
        user_df = load_pickle_or_parquet(self.user_df_path)
        
        # turns out that the counts in the user_df don't match those in df.
        # it could be that posts were thrown out at some point, maybe because they were empty
        # or deleted.
        ds("adding total user posts")
        cnts_dict = df.groupby('author').size().to_dict()
        df['total_user_posts'] = df['author'].map(cnts_dict)
        
        ds('adding post numbers')
        df = df.sort_values(by=['author', 'seconds'])
        df['post_number'] = df.groupby('author').cumcount()
        
        ds("getting first date")
        first_date = sorted(user_df.first_post.tolist())[0]
        
        ds("labeling with true dates")
        
        df['true_date'] = first_date + pd.to_timedelta(df['seconds'], unit='s')

        ds("filling experience")
        df, k = fill_experience(df, True)
        params = {
            "k": k,
            "created": str(datetime.now())
        }

        save_to_json(params, self.json_path)
        
        self.display_status("writing")
        
        df.to_parquet(self.output_path)
        os.remove(self.df_path)
        

if __name__ == '__main__':
    print("starting")
    Tile = LabelTrueDates(sys.argv[1], sys.argv[2], sys.argv[3])
    Tile.render_content()