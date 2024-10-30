print("starting")
import pickle
import json
import sys
import os
import re
import datetime
import pandas as pd
import numpy as np
from utilities import ds, html_table
from plot_trajectory_snippet2 import plot_trajectory

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)

import os

def find_subfolder(base_path, end_string):
    for root, dirs, files in os.walk(base_path):
        for dir_name in dirs:
            if dir_name.endswith(end_string):
                return os.path.join(root, dir_name)
    return None  # If no subfolder is found

def find_unpadded_model(base_path):
    for root, dirs, files in os.walk(base_path):
        for dir_name in dirs:
            if "_snapshots_" in dir_name:
                the_path = os.path.join(root, dir_name)
                param_df = pd.read_csv(f"{the_path}/parameters.txt", sep=":\t", names=["key", "value"], index_col="key")
                if int(param_df.loc["end_buffer"].value) == 0:
                    print(f"Found unpadded model at {the_path}")
                    return the_path
    return None  # 

print("done with globals")
class ExploreExperience():
    def __init__(self, subreddit, base_path):
        self.subreddit = subreddit
        self.base_path = base_path
        self.snapshot_folder = find_unpadded_model(f"{base_path}/{subreddit}")
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

    def pull_param_vals(self):
        param_df = pd.read_csv(f"{self.snapshot_folder}/parameters.txt", sep=":\t", names=["key", "value"], index_col="key")
        keys = param_df.index.tolist()
        for key in keys:
            setattr(self, key, param_df.loc[key].value)
        return
        
    def render_content(self):
        ds("Getting snapshot params")
        global kb_model
        
        self.pull_param_vals()
        
        ds("Reading exp_df")
        exp_df = load_pickle_or_parquet(f"{self.base_path}/{self.subreddit}/{self.subreddit}_df_exp_true.parquet")
            
        score_start = f"{self.subreddit}_scored"
        score_df = None
        for item in os.listdir(self.snapshot_folder):
            if item.startswith(score_start):
                ds("Reading score_df")
                score_df = load_pickle_or_parquet(os.path.join(self.snapshot_folder, item))
                break
        if score_df is None:
            return "Didn't find score_df"
            
        score_df["experience"] = exp_df["experience"]
        score_df = score_df.dropna(subset=['experience'])
        smonth_num = int(self.start_month)
        emonth_num = int(self.end_month)
        self.start_year = int(self.start_year)
        self.end_year = int(self.end_year)
        
        start_date = datetime.datetime(self.start_year, smonth_num, 1)
        end_date = datetime.datetime(self.end_year, emonth_num, 1)
        score_df = score_df[score_df["true_date"] >= start_date]
        score_df = score_df[score_df["true_date"] <= end_date]
        
        self.overall_mean = score_df["experience"].mean()
        self.overall_median = score_df["experience"].median()
        overall = {
            "mean": round(self.overall_mean, 1),
            "median": round(self.overall_median, 1),
            "k": round(exp_df["dt"].mean(), 1)
        }
        
        result_list = []
        
        for year in range(self.start_year, self.end_year + 1):
            smonth = smonth_num if year == self.start_year else 1
            emonth = emonth_num if year == self.end_year else 12
            
            for month in range(smonth, emonth + 1):
                ds(f"Processing year {year} month {month}")
                month_df = score_df[(score_df['true_date'].dt.year == year) & (score_df['true_date'].dt.month == month)]
                avg_exp = month_df["experience"].mean()
                median_exp = month_df["experience"].median()
                if not np.isnan(avg_exp):
                    avg_exp = round(avg_exp, 1)
                if not np.isnan(median_exp):
                    median_exp = round(median_exp, 1)
                result_list.append({
                    "true_month": f"{year}-{month}",
                    "avg_exp": avg_exp,
                    "median_exp": median_exp
                })
        
        self.result_df = pd.DataFrame(result_list)
        the_html = html_table(overall) + html_table(self.result_df)
        results = {
            "result_df": getattr(Tile, "result_df"),
            "overall_median": getattr(Tile, "overall_median"),
            "overall_mean": getattr(Tile, "overall_mean"),
            "parameters": self.get_parameters()
        }
        self.result_df.to_parquest(f"{self.base_path}/{self.subreddit}/{self.subreddit}_exp_by_month.parquet")
        html += plot_trajectory(self.result_df, "true_month", "avg_exp", marker_size=8)
        with open(f"{self.base_path}/{self.subreddit}/exp_by_month.html", 'w') as file:
            file.write(html)

if __name__ == '__main__':
    print("starting")
    # subreddit, base_path
    Tile = ExploreExperience(sys.argv[1], sys.argv[2])
    Tile.render_content()