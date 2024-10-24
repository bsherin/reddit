print("starting create_snapshot_models.py")
import pickle
import json
import sys
import os
import traceback
import pandas as pd
import numpy as np
import pickle
import random
import string
from katz_class import KatzBigramLM

CORPUS_START_YEAR = 2006
CORPUS_START_MONTH = 5
CORPUS_END_YEAR = 2022
CORPUS_END_MONTH = 12


CORPUS_START = pd.Timestamp(year=CORPUS_START_YEAR, month=CORPUS_START_MONTH, day=1)
CORPUS_END = pd.Timestamp(year=CORPUS_END_YEAR, month=CORPUS_END_MONTH, day=31)

month_list = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]

def month_number(month_name):
    return month_list.index(month_name) + 1

def handle_exception(ex, special_string=None):
    error_string = get_traceback_message(ex, special_string)
    print(error_string)
    return error_string

def get_traceback_message(e, special_string=None):
    if special_string is None:
        template = "<pre>An exception of type {0} occured. Arguments:\n{1!r}\n"
    else:
        template = special_string + "<pre>\n" + "An exception of type {0} occurred. Arguments:\n{1!r}\n"
    error_string = template.format(type(e).__name__, e.args)
    error_string += traceback.format_exc() + "</pre>"
    return error_string

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)

def find_longest_true_sequence(bool_list):
    current_start = None
    current_length = 0
    max_start = None
    max_length = 0
    
    for i, value in enumerate(bool_list):
        if value:
            if current_start is None:
                current_start = i  # Start a new sequence
            current_length += 1
        else:
            if current_start is not None:
                if current_length > max_length:  # Check if the current sequence is the longest
                    max_length = current_length
                    max_start = current_start
                # Reset current sequence
                current_start = None
                current_length = 0
    
    # Handling the case where the list ends with True
    if current_start is not None and current_length > max_length:
        max_length = current_length
        max_start = current_start
    
    # Calculating the end index of the longest sequence
    max_end = None
    if max_start is not None:
        max_end = max_start + max_length - 1
    
    return (max_start, max_end)


def ds(txt):
    print(txt)

print("done with globals")
params = ["working_directory", "subreddit_name", "users_per_month", "posts_per_user", 
          "start_buffer", "end_buffer", "min_user_posts", "leave_unknown", "max_discount"]
class LmSnapshotAuto():
    def __init__(self, jsonfile, uid):
        self.uid = uid
        with open(jsonfile, 'r') as file:
            config = json.load(file)

        for param in params:
            if param in config:
                setattr(self, param, config[param])
            else:
                setattr(self, param, None)
        
        self.df_file = f"{self.working_directory}/{self.subreddit_name}_df_true.parquet"
        self.user_df_file = f"{self.working_directory}/{self.subreddit_name}_user_data.parquet"
        self.output_location = self.working_directory
        self.output_folder_name = f"{self.subreddit_name}_snapshots"

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

    def dstable(self, txt):
        print(txt)

    def modify_options(self):
        return self.options
    
    def get_good_users(self, user_df):
        good_users = user_df
        good_users["total_posts"] = good_users.apply(lambda row: row["top_level_comments"] + row["submissions"], 1)
        good_users = good_users[good_users["top_level_comments"] >= self.min_user_posts]
        return good_users.index.tolist()
    
    def create_month_model(self, df, month, year):
        def select_random_posts(group):
            return group.sample(n=self.posts_per_user, random_state=1)
        try:
            self.dstable(f"Getting posts for month {month} year {year}")
            df['author'] = df['author'].astype(str)
            
            month_df = df[(df['true_date'].dt.year == year) & (df['true_date'].dt.month == month)]
            post_counts = month_df.groupby('author').size()
            users = month_df.author.unique()
            candidate_users = post_counts[post_counts >= self.posts_per_user]
            self.month_table.append({
                "month": month, "year": year, "nposts": len(month_df), "nusers": len(users), 
                "cand_users": len(candidate_users), "success": "pending"
            })
            # we assign status_stub because KatzBigramLM looks for it
            self.dstable(f"Getting posts for month {month} year {year}")
            culist = list(candidate_users.keys())
            if len(month_df) < self.min_posts_per_month:
                self.month_table[-1]["success"] = False
                return {"success": False, "reason": "too few posts", "month": month, "year": year}
            if len(users) < self.min_users_per_month:
                self.month_table[-1]["success"] = False
                return {"success": False, "reason": "nusers less than min_users_per_month", "month": month, "year": year}
            if len(candidate_users) < self.users_per_month:
                self.month_table[-1]["success"] = False
                return {"success": False, "reason": f"candidate users {len(candidate_users)} less than users per month {self.users_per_month}", "month": month, "year": year}
            selected_users = random.sample(culist, self.users_per_month)
            user_filtered_df = month_df[month_df['author'].isin(selected_users)]
            random_posts = user_filtered_df.groupby("author").apply(select_random_posts).reset_index(drop=True)
            if "post_id" in random_posts.columns:
                post_ids = random_posts.post_id.tolist()
            else:
                post_ids = random_posts.index.tolist()
            self.dstable(f"building language model for month {month} year {year}")
            lm = KatzBigramLM(leave_unknown=self.leave_unknown, max_discount=self.max_discount)
            lm.fit(random_posts)
            self.month_table[-1]["success"] = True
            return {"success": True, "month": month, "year": year, "lm_dict": lm.__getstate__(), "post_ids": post_ids}
        except Exception as ex:
            self.month_table[-1]["success"] = False
            return {"success": False, "reason": handle_exception(ex), "month": month, "year": year}
    
    def get_parameters(self):
        plist = []
        plist.append({"name": "uid", "value": self.uid})

        for param in params:
            if hasattr(self, param):
                plist.append({"name": param, "value": getattr(self, param)})

        plist += [
            {"name": "start_month", "value": self.start_month},
            {"name": "start_year", "value": self.start_year},
            {"name": "end_month", "value": self.end_month},
            {"name": "end_year", "value": self.end_year}
        ]
        return plist
    
    def get_param_string(self):
        plist = self.get_parameters()
        pstr = ""
        for p in plist:
            pstr += f"{p['name']}:\t{str(p['value'])}\n"
        return pstr
    
    def render_content(self):
        class BreakLoops(Exception): 
            pass
        
        self.min_users_per_month = self.users_per_month * 2
        self.min_posts_per_month = self.posts_per_user * self.min_users_per_month 
        
        self.month_table = []
        self.status_stub = ""
        
        output_path = f"{self.output_location}/{self.output_folder_name}_{self.uid}"
        snapshot_path = f"{output_path}/snapshots"
        print(f"creating snapshot folder {snapshot_path}")
        os.makedirs(snapshot_path)
            
        print("reading data")
        
        df = load_pickle_or_parquet(self.df_file)
        user_df = load_pickle_or_parquet(self.user_df_file)
        
        first_date = user_df.first_post.min()
        
        start_buffer_td = pd.Timedelta(weeks=(self.start_buffer * 4))
        end_buffer_td = pd.Timedelta(weeks=(self.end_buffer * 4))
        
        if first_date < CORPUS_START + start_buffer_td:
            first_date = CORPUS_START + start_buffer_td
            
        if first_date.month == 12:
            start_month = 1
            start_year = int(first_date.year + 1)
        else:
            start_month =int(first_date.month + 1)
            start_year = int(first_date.year)
        
        end_date = CORPUS_END - end_buffer_td
        
        if end_date.month == 1:
            end_month = 12
            end_year = end_date.year - 1
        else:
            end_month = end_date.month - 1
            end_year = end_date.year
        
        ds("pruning users")
        if self.min_user_posts > 1:
            good_user_list = self.get_good_users(user_df)
            df = df[df['author'].isin(good_user_list)]
        
        ds("building models")
        result = None
        all_used_posts = []
        success_list = []
        try:
            for year in range(start_year, end_year + 1):
                if year == start_year:
                    smonth = start_month
                else:
                    smonth = 1
                for month in range(smonth, 12):
                    if year == end_year and month > end_month:
                        break
                    result = None
                    result = self.create_month_model(df, month, year)
                    mstring = f"{month_list[month - 1]}-{str(year)}"
                    if result["success"]:
                        success_list.append([month, year, True])
                        all_used_posts.append(result["post_ids"])
                        self.dstable(f"successfully created model for month {month} year {year}")
                        fpath = f"{snapshot_path}/{mstring}"
                        with open(fpath, "wb") as f:
                            pickle.dump(result, f)
                    else:
                        success_list.append([month, year, False])
                        ostring = f"failed for month {month} year {year} reason {result['reason']}"
                        print(ostring)
                        self.dstable(ostring)
         
            used_path = f"{output_path}/used_posts.pkl"
            with open(used_path, "wb") as f:
                pickle.dump(all_used_posts, f)
            table_path = f"{output_path}/month_table.pkl"
            with open(table_path, "wb") as f:
                pickle.dump(self.month_table, f)
        
            bool_list = [suc[2] for suc in success_list]
            sindex, eindex = find_longest_true_sequence(bool_list)
            self.start_month = success_list[sindex][0]
            self.start_year = success_list[sindex][1]
            self.end_month = success_list[eindex][0]
            self.end_year = success_list[eindex][1]
            edate = success_list[eindex]
            with open(f"{output_path}/parameters.txt", "w") as f:
                f.write(self.get_param_string())
        except BreakLoops:
            if result is not None and "reason" in result:
                reason = result["reason"]
            else:
                reason = "none"
            return f"failed in month {month} of year {year} with reason {reason}"

if __name__ == '__main__':
    print("starting")
    Tile = LmSnapshotAuto(sys.argv[1], sys.argv[2])
    Tile.render_content()