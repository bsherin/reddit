print("starting")
import json
import sys
import pandas as pd
from utilities import html_table

from utilities import ds

stage_kind_dict = {
    "num_phases": "phase",
    "raw_post_count": "posts",
    "time": "weeks",
    "experience": "pseudo weeks",
    "ntokens_bins": "ntokens"
}

bin_key_dict = {
    "num_phases": "num_phases",
    "raw_post_count": "post_bin",
    "time": "time_bin_weeks",
    "experience": "exp_bin_size",
    "ntokens_bins": "ntokens_bin_size"
}

print("done with globals")
class BuildTrajectoryReport():
    def __init__(self, jsonfile, subreddit, snapshot_uid, base_path):
        with open(jsonfile, 'r') as file:
            config = json.load(file)
        self.subreddit_name = subreddit
        self.working_directory = f"{base_path}/{self.subreddit_name}"
        self.uid = snapshot_uid
        self.snaphot_folder = f"{base_path}/{subreddit}/{subreddit}_snapshots_{self.uid}"
        self.report_file = f"{self.snaphot_folder}/{subreddit}_{self.uid}_report.html"

        self.min_posts = config["min_posts"] if "min_posts" in config else 2000
        self.marker_size = config["marker_size"] if "marker_size" in config else 8
        self.option_names = ["min_posts", "marker_size"]
        with open(f"{self.snaphot_folder}/trajectory_key_info.json", 'r') as file:
            self.key_info = json.load(file)
        return

    def display_status(self, text):
        print(text)

    def get_parameters(self):
        plist = []
        for opt_name in self.option_names:
            plist.append({"name": opt_name, "value": getattr(self, opt_name)})
        return plist

    def handle_log_tile(self):
        self.log_it(self.report, summary=self.summary)
    def render_content(self):
        import sys
        import os
        from plot_trajectory_snippet import plot_trajectory
        

        param_df = pd.read_csv(f"{self.snaphot_folder}/parameters.txt", sep=":\t", engine="python", names=["key", "value"], index_col="key")
        # the_html = """
        #     <style>
        #         .trajectory-report td {
        #             padding-top: 8px !important;
        #             padding-bottom: 8px !important;
        #         }
        #     </style>
        # """
        with open("styles.html", 'r') as file:
            the_html = file.read()
        self.summary = f"{self.subreddit_name}_{self.uid}"
        
        the_html += "<div class='trajectory-report'>"
        the_html += f"<h3>{self.summary}</h3>"
        the_html += "<h4 style='margin-top:20px'>Model Parameters</h4>"
        the_html += html_table(param_df)
        the_html += "<h4 style='margin-top:20px'>ScoresToTrajectories Parameters</h4>"
        the_html += html_table(self.key_info)
        the_html += "</div>"
        
        for kind, x_col in stage_kind_dict.items():
            try:
                ds(f"processing kind {kind}")
                df = pd.read_parquet(f"{self.snaphot_folder}/{kind}_trajectory_df.parquet")
                if type(df) == str or len(df) == 0:
                    continue
                
                tstring = f"<b>score vs {x_col}</b><br>{bin_key_dict[kind]}={self.key_info[bin_key_dict[kind]]}"
                the_html += plot_trajectory(df, x_col, "score", 
                                            marker_size=self.marker_size, title_string=tstring)
                if "nposts" in df.columns:
                    the_html += plot_trajectory(df, x_col, "score", fn="nposts", fv=self.min_posts, fk=">=", 
                                                marker_size=self.marker_size, top_margin=85, title_string=tstring)
            except Exception as e:
                print(f"Error processing {kind}: {e}")
                continue
        
        self.report = the_html
        

        with open(self.report_file, 'w') as file:
            file.write(the_html)

if __name__ == '__main__':
    print("starting")
    # jsonfile, subreddit, snapshot_uid, base_path)
    Tile = BuildTrajectoryReport(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    Tile.render_content()