print("starting")
import pickle
import json
import sys
import re
import os
import pandas as pd

from plot_trajectory_snippet_errors import plot_trajectory
from utilities import html_table

def ds(text):
    print(text)

stage_kind_dict = {
    "num_phases": "phase",
    "raw_post_count": "posts",
    "time": "weeks",
    "experience": "pseudo weeks",
    # "ntokens_bins": "ntokens"
}

bin_key_dict = {
    "num_phases": "num_phases",
    "raw_post_count": "post_bin",
    "time": "time_bin_weeks",
    "experience": "exp_bin_size",
    # "ntokens_bins": "ntokens_bin_size"
}
class BuildAverageTrajectoryReport():
    def __init__(self, source, fn="nposts", fv=2000, fk=">=", marker_size=6):

        self.source = source
        self.fn = fn
        self.fv = fv
        self.fk = fk
        self.marker_size = marker_size
        self.html_table = html_table
        return

    def display_status(self, text):
        print(text)

    def render_content(self):
        import sys
        import os
        if "plot_trajectory_snippet" in sys.modules:
            del sys.modules["plot_trajectory_snippet"]

        
        source = self.source
        param_df = source["param_df"]
        subreddit = source["subreddit"]
        uids = source["uids"]
        run_numbers = source["run_numbers"]
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
        the_html += f"<div>run_numbers: {str(run_numbers)}</div>"
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
            the_html += plot_trajectory(df, x_col, "score", show_errors=True, fit_curve=True,
                                        marker_size=self.marker_size, title_string=tstring)
            if self.fn in df.columns:
                the_html += plot_trajectory(df, x_col, "score", fn=self.fn, fv=self.fv, fk=self.fk, 
                                            marker_size=self.marker_size, top_margin=85, title_string=tstring)
                the_html += plot_trajectory(df, x_col, "score", fn=self.fn, fv=self.fv, fk=self.fk, 
                                            show_errors=True, fit_curve=True, 
                                            marker_size=self.marker_size, top_margin=85, title_string=tstring)
        
        return the_html
    
if __name__ == '__main__':
    print("starting")
    # source, fn, fv, fk, marker_size=8
    source_pickle = sys.argv[1]
    print("got source pickle", source_pickle)
    with open(source_pickle, "rb") as f:
        source = pickle.load(f)
    folder = os.path.dirname(source_pickle)
    fn = sys.argv[2]
    fv = float(sys.argv[3])
    fk = sys.argv[4]
    Tile = BuildAverageTrajectoryReport(source, fn, fv, fk)
    print("rendering content")
    the_html = Tile.render_content()
    print("go the html")
    if source["is_exp"]:
        fname = f"{source['subreddit']}_avg_exp_{fn}_{fk}_{str(fv)}"
    else:    
        fname = f"{source['subreddit']}_avg_{fn}_{fk}_{str(fv)}"
    print("writing to", f"{folder}/{fname}.html")
    with open(f"{folder}/{fname}.html", "w") as f:
        f.write(the_html)
    print("done")
    