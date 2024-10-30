print("starting")
import pickle
import json
import sys
import pickle
import os
import pandas as pd
from pandas import Timedelta
import re
import json

y_axis_labels = {
    "num_phases": "phase",
    "raw_post_count": "posts",
    "time": "weeks",
    "experience": "pseudo weeks",
    "ntokens_bins": "ntokens"
}

stage_kinds = ["num_phases", "raw_post_count", "time", "experience"]

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)

def is_exp_sampling(param_df):
    return "threshold_in_days" in param_df.index

def compare_dataframes(df1, df2):
    if df1.index.equals(df2.index) and (df1['value'] == df2['value']).all():
        return True
    else:
        return False

def compare_dicts(d1, d2):
    for k in d1.keys():
        if not d1[k] == d2[k]:
            return False
    return True
    

print("done with globals")
class AverageTrajectories():
    def __init__(self, jsonfile):
        import textwrap
        with open(jsonfile, 'r') as file:
            config = json.load(file)
        self.folder_of_models = config["folder_of_models"] if "folder_of_models" in config else None
        self.output_file = config["output_file"] if "output_file" in config else None
        self.option_names = ["folder_of_models", "output_file"]
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
        trajectories = []
        params = []
        
        subreddit = None
        
        uids = []
        seeds = []
        
        common_param_df = None
        common_key_info = None
        
        for item in os.listdir(self.folder_of_models):
            item_path = os.path.join(self.folder_of_models, item)
            # Check if the item is a directory
            if os.path.isdir(item_path):
                fdict = {}
                for stage_kind in stage_kinds:
                    fdict[stage_kind] = load_pickle_or_parquet(f"{item_path}/{stage_kind}_trajectory_df.parquet")
                trajectories.append(fdict)
                param_df = pd.read_csv(f"{item_path}/parameters.txt", sep=":\t", names=["key", "value"], index_col="key")
                uids.append(param_df.loc["uid"].value)
                seeds.append(param_df.loc["seed"].value)
                param_df = param_df.drop(["uid", "seed"])
                if subreddit is None:
                    bn = os.path.basename(item_path)
                    subreddit = re.findall("^(.*?)_snapshots", bn)[0]
                    is_exp = is_exp_sampling(param_df)
                    common_param_df = param_df
                if not compare_dataframes(param_df, common_param_df):
                    the_html = f"Got unmatched params for uid {uids[-1]} with original uid {uids[0]}<br>"
                    the_html += self.html_table(param_df, sidebyside=True)
                    the_html += self.html_table(common_param_df, sidebyside=True)
                    return the_html
                with open(f"{item_path}/trajectory_key_info.json", "r") as f:
                    key_info = json.load(f)
                key_info["k"] = round(float(key_info["k"]), 1)
                if common_key_info is None:
                    common_key_info = key_info
                if not compare_dicts(key_info, common_key_info):
                    the_html = f"Got unmatched key_info for uid {uids[-1]} with original uid {uids[0]}<br>"
                    the_html += self.html_table(key_info, sidebyside=True)
                    the_html += self.html_table(common_key_info, sidebyside=True)
        
        self.param_df = common_param_df
        self.key_info = common_key_info
        self.uids = uids
        self.seeds = seeds
        self.subreddit = subreddit
        self.is_exp = is_exp
        
        if self.is_exp:
            self.table_html = f"<h4>{subreddit}_exp</h4>"
        else:
            self.table_html = f"<h4>{subreddit}</h4>"
        self.table_html += self.html_table(common_param_df, sidebyside=True)
        self.table_html += self.html_table(common_key_info, sidebyside=True)
        self.table_html += "<br>"
        ds("computing averages")
        for stage_kind in stage_kinds:
            dfs = []
            for fdict in trajectories:
                dfs.append(fdict[stage_kind])
            combined_df = pd.concat(dfs)
            result_df = combined_df.groupby(y_axis_labels[stage_kind]).mean().reset_index()
            setattr(self, f"{stage_kind}_trajectory_df", result_df)
        results = {
            "num_phases_trajectory_df": getattr(Tile, "num_phases_trajectory_df"),
            "raw_post_count_trajectory_df": getattr(Tile, "raw_post_count_trajectory_df"),
            "time_trajectory_df": getattr(Tile, "time_trajectory_df"),
            "experience_trajectory_df": getattr(Tile, "experience_trajectory_df"),
            "ntokens_bins_trajectory_df": getattr(Tile, "ntokens_bins_trajectory_df"),
            "param_df": getattr(Tile, "param_df"),
            "key_info": getattr(Tile, "key_info"),
            "uids": getattr(Tile, "uids"),
            "subreddit": getattr(Tile, "subreddit"),
            "seeds": getattr(Tile, "seeds"),
            "is_exp": getattr(Tile, "is_exp"),
            "parameters": self.get_parameters()
        }
        if self.output_file is not None:
            f = open(self.output_file, "wb")
            pickle.dump(results, f)
            f.close()
            return
        else:
            return results

if __name__ == '__main__':
    print("starting")
    Tile = AverageTrajectories(sys.argv[1])
    Tile.render_content()