print("starting")
import pickle
import json
import sys
import re
import pandas as pd


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
class BuildAverageTrajectoryReport():
    def __init__(self, jsonfile):
        import textwrap
        with open(jsonfile, 'r') as file:
            config = json.load(file)
        self.TrajectoriesSource = config["TrajectoriesSource"] if "TrajectoriesSource" in config else None
        self.min_posts = config["min_posts"] if "min_posts" in config else 2000
        self.marker_size = config["marker_size"] if "marker_size" in config else 8
        self.output_file = config["output_file"] if "output_file" in config else None
        self.option_names = ["TrajectoriesSource", "min_posts", "marker_size", "output_file"]
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

    def handle_log_tile(self):
        self.log_it(self.report, summary=self.summary)
    def render_content(self):
        import sys
        import os
        if "plot_trajectory_snippet" in sys.modules:
            del sys.modules["plot_trajectory_snippet"]
        
        tactic_import("plot_trajectory_snippet")
        plot_trajectory = plot_trajectory_snippet.plot_trajectory
        
        source = Tiles[self.TrajectoriesSource]
        param_df = source["param_df"]
        subreddit = source["subreddit"]
        uids = source["uids"]
        seeds = source["seeds"]
        key_info = source["key_info"]
        is_exp = source["is_exp"]
        
        
        the_html = """
            <style>
                .trajectory-report div {
                    margin-top: 10px
                }
                .trajectory-report td {
                    padding-top: 8px !important;
                    padding-bottom: 8px !important;
                }
                .sidebyside-table {
                    vertical-align: top;
                    margin-top: 25px;
                    margin-bottom: 25px;
                    margin-right: 20px;
                }
            </style>
        """
        if is_exp:
            self.summary = f"{subreddit}_avg_exp"
        else:
            self.summary = f"{subreddit}_avg"
        
        the_html += "<div class='trajectory-report'>"
        the_html += f"<h5>{self.summary}</h5>"
        the_html += f"<div>uids: {str(uids)}</div>"
        the_html += f"<div>seeds: {str(seeds)}</div>"
        the_html += self.html_table(param_df, title="Model Parameters", sidebyside=True)
        the_html += self.html_table(key_info, title="ScoresToTrajectories Parameters", sidebyside=True)
        the_html += "</div>"
        
        for kind, x_col in stage_kind_dict.items():
            ds(f"processing kind {kind}")
            df = source[f"{kind}_trajectory_df"]
            if df is None or type(df) == str or len(df) == 0:
                continue
            
            tstring = f"<b>score vs {x_col}</b><br>{bin_key_dict[kind]}={key_info[bin_key_dict[kind]]}"
            the_html += plot_trajectory(df, x_col, "score", 
                                        marker_size=self.marker_size, title_string=tstring)
            if "nposts" in df.columns:
                the_html += plot_trajectory(df, x_col, "score", fn="nposts", fv=self.min_posts, fk=">=", 
                                            marker_size=self.marker_size, top_margin=85, title_string=tstring)
        
        self.report = the_html
        
        results = {
            "report": getattr(Tile, "report"),
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
    Tile = BuildAverageTrajectoryReport(sys.argv[1])
    Tile.render_content()