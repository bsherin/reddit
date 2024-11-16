### This script is used to generate the average trajectory report for a given subreddit.
### The script takes in the following arguments:
###     1. The folder containing the snapshots of the models for the subreddit.
###     2. A boolean value indicating whether the models are generated using the exponential sampling method.
###     3. The minimum number of posts required for a user to be included in the analysis.
### Produces the following output:
###     - {subreddit}_avg_error.html or {subreddit}_avg_exp_error.htm: The average trajectory report for the subreddit.
###     - {subreddit}_avg_error_results.pkl {subreddit}_avg_exp_eerror_results.pkl: The results of the analysis saved in a pickle file.
###     - trajectory df for each stage kind
###     - parameters.txt

import pickle
import json
import sys
import pickle
import os
import pandas as pd
from pandas import Timedelta
import re
import json

from build_average_trajectory_report_user_avg import BuildAverageTrajectoryReport
from utilities import html_table, save_to_json

x_axis_labels = {
    "num_phases_user_avg": "phase",
    "raw_post_count_uvg": "posts",
    "raw_post_count_uvg_median": "posts"
}

stage_kinds = ["num_phases_user_avg", "raw_post_count_uvg", "raw_post_count_uvg_median"]

def ds(text):
    print(text)

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
class AverageTrajectoriesUserAvg():
    def __init__(self, folder_of_models, use_exp, min_posts):
        self.folder_of_models = folder_of_models
        self.html_table = html_table
        self.min_posts = min_posts
        self.use_exp = use_exp
        return
    
    def display_status(self, text):
        print(text)

    def get_param_string(self, param_df):
        pdict = param_df["value"].to_dict()
        pstr = ""
        for p, v in pdict.items():
            pstr += f"{p}:\t{str(v)}\n"
        return pstr
    

    def render_content(self):
        trajectories = []
        params = []
        
        subreddit = None
        
        uids = []
        run_numbers = []
        
        common_param_df = None
        common_key_info = None

        if self.use_exp:
            output_folder = f"{self.folder_of_models}/exp_user_avg"
        else:
            output_folder = f"{self.folder_of_models}/user_avg"
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        print("looping over folder")
        traj_folder_name = f"trajectory_data_user_avg"
        for item in os.listdir(self.folder_of_models):
            model_path = os.path.join(self.folder_of_models, item)
            # Check if the item is a directory
            print("got item path", model_path)
            if os.path.isdir(model_path):
                if "_snapshots" not in model_path:
                    continue
                item_path = os.path.join(model_path, traj_folder_name)
                if not os.path.isdir(item_path):
                    continue
                param_df = pd.read_csv(f"{model_path}/parameters.txt", sep=":\t", engine="python", names=["key", "value"], index_col="key")
                is_exp = "threshold_in_days" in param_df.index
                if self.use_exp != is_exp:
                    continue
                fdict = {}
                with open(f"{item_path}/trajectory_key_info.json", "r") as f:
                    key_info = json.load(f)
                del key_info["model"]
                stage_names = {
                    "num_phases_user_avg": f"num_phases_user_avg_{key_info['num_phases']}",
                    "raw_post_count_uvg": f"raw_post_count_uvg_{key_info['num_posts']}",
                    "raw_post_count_uvg_median": f"raw_post_count_uvg_median_{key_info['median_posts']}"
                }
                for stage_kind in stage_kinds:
                    fdict[stage_kind] = load_pickle_or_parquet(f"{item_path}/{stage_names[stage_kind]}_trajectory_df.parquet")
                trajectories.append(fdict)
                
                uids.append(param_df.loc["uid"].value)
                if "run_number" in param_df.index:
                    run_numbers.append(param_df.loc["run_number"].value)
                    param_df = param_df.drop(["uid", "run_number", "use_run_number_as_seed"])
                else:
                    run_numbers.append(param_df.loc["seed"].value)
                    param_df = param_df.drop(["uid", "seed"])
                if subreddit is None:
                    bn = os.path.basename(model_path)
                    subreddit = re.findall("^(.*?)_snapshots", bn)[0]
                    is_exp = is_exp_sampling(param_df)
                    common_param_df = param_df
                if not compare_dataframes(param_df, common_param_df):
                    print(f"Got unmatched params for uid {uids[-1]} with original uid {uids[0]}<br>")

                if common_key_info is None:
                    common_key_info = key_info
                if not compare_dicts(key_info, common_key_info):
                    print(f"Got unmatched key_info for uid {uids[-1]} with original uid {uids[0]}<br>")
        print("done looping over folder")
        self.param_df = common_param_df
        self.key_info = common_key_info
        self.uids = uids
        self.run_numbers = run_numbers
        self.subreddit = subreddit

        stage_names = {
            "num_phases_user_avg": f"num_phases_user_avg_{self.key_info['num_phases']}",
            "raw_post_count_uvg": f"raw_post_count_uvg_{self.key_info['num_posts']}",
            "raw_post_count_uvg_median": f"raw_post_count_uvg_median_{self.key_info['median_posts']}"
        }
        
        if self.use_exp:
            self.table_html = f"<h4>{subreddit}_exp</h4>"
        else:
            self.table_html = f"<h4>{subreddit}</h4>"
        self.table_html += self.html_table(common_param_df, sidebyside=True)
        self.table_html += self.html_table(common_key_info, sidebyside=True)
        self.table_html += "<br>"
        ds("computing averages")
        for stage_kind in stage_kinds:
            stage_name = stage_names[stage_kind]
            dfs = []
            for fdict in trajectories:
                dfs.append(fdict[stage_kind])
            xlabel = x_axis_labels[stage_kind]
            combined_df = pd.concat([df[[xlabel, 'score']] for df in dfs])
            result_df = combined_df.groupby(xlabel).agg(['mean', 'std'])
            result_df.columns = ['score', 'std_dev']
            result_df = result_df.reset_index()
            result_df["nusers"] = dfs[0]["nusers"]
            setattr(self, f"{stage_name}_trajectory_df", result_df)
            result_df.to_parquet(f"{output_folder}/{stage_name}_trajectory_df.parquet")
        results = {
            "num_phases_trajectory_df": getattr(self, f'{stage_names["num_phases_user_avg"]}_trajectory_df'),
            "raw_post_count_trajectory_df": getattr(self, f'{stage_names["raw_post_count_uvg"]}_trajectory_df'),
            "raw_post_count_median_trajectory_df": getattr(self, f'{stage_names["raw_post_count_uvg_median"]}_trajectory_df'),
            "param_df": getattr(self, "param_df"),
            "key_info": getattr(self, "key_info"),
            "uids": getattr(self, "uids"),
            "subreddit": getattr(self, "subreddit"),
            "run_numbers": getattr(self, "run_numbers"),
            "is_exp": getattr(self, "use_exp"),
        }
        print("writing results")
        save_to_json(results["key_info"], f"{output_folder}/trajectory_key_info.json")
        with open(f"{output_folder}/parameters.txt", "w") as f:
            f.write(self.get_param_string(results["param_df"]))
        # source, fn, fv, fk, marker_size=8
        rclass = BuildAverageTrajectoryReport(results)
        the_html = rclass.render_content()
        if self.use_exp:
            fname = f"{subreddit}_avg_exp_error_user_avg_{key_info['num_posts']}"
        else:
            fname = f"{subreddit}_avg_error_user_avg_{key_info['num_posts']}"
        with open(f"{output_folder}/{fname}.html", "w") as f:
            f.write(the_html)
        with open(f"{output_folder}/{fname}_results.pkl", "wb") as f:
            pickle.dump(results, f)

if __name__ == '__main__':
    print("starting")
    use_exp = sys.argv[2].lower() == 'true'
    # folder_of_models, use_exp, min_posts=2000
    print("got folder", sys.argv[1])
    Tile = AverageTrajectoriesUserAvg(sys.argv[1], use_exp, sys.argv[3])
    Tile.render_content()