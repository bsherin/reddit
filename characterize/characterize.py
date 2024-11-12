### This script is used to generate a report on the characteristics of a subreddit.
### It reads the df_true and user_data dataframes
### The report is named {subreddit_name}_characteristics_report.html

print("starting")
import pickle
import json
import sys
import pandas as pd
import os, re

from utilities import html_table, flatten, ds
from plot_trajectory_snippet2 import plot_trajectory

seconds_per_week = 86400 * 6

def get_good_users(self, user_df):
    good_users = user_df
    good_users["total_posts"] = good_users.apply(lambda row: row["top_level_comments"] + row["submissions"], 1)
    good_users = good_users[good_users["top_level_comments"] >= self.min_user_posts]
    return good_users.index.tolist()

def get_month_count(self, df, month, year, mnumber):
    month_df = df[(df['true_date'].dt.year == year) & (df['true_date'].dt.month == month)]
    return {"month": month, "year": year, "posts": len(month_df), "month_number": mnumber}

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

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)

def ds(text):
    print(text)

print("done with globals")
class SubredditCharacteristicsReport():
    def __init__(self, jsonfile, subreddit, base_path):
        import textwrap
        with open(jsonfile, 'r') as file:
            config = json.load(file)
        self.subreddit_name = subreddit
        self.working_directory = f"{base_path}/{self.subreddit_name}"

        self.df_parquet = f"{self.working_directory}/{self.subreddit_name}_df_true.parquet"
        self.user_df_parquet = f"{self.working_directory}/{self.subreddit_name}_user_data.parquet"

        self.min_user_posts = config["min_user_posts"] if "min_user_posts" in config else 1
        self.marker_size = config["marker_size"] if "marker_size" in config else 8
        self.option_names = ["df_parquet", "user_df_parquet", "min_user_posts", "marker_size"]
        return

    def display_status(self, text):
        print(text)

    def get_parameters(self):
        plist = []
        for opt_name in self.option_names:
            plist.append({"name": opt_name, "value": getattr(self, opt_name)})
        return plist

    def get_good_users(self, user_df):
        good_users = user_df
        good_users["total_posts"] = good_users.apply(lambda row: row["top_level_comments"] + row["submissions"], 1)
        good_users = good_users[good_users["top_level_comments"] >= self.min_user_posts]
        return good_users.index.tolist()
    
    def get_month_count(self, df, month, year, mnumber):
        month_df = df[(df['true_date'].dt.year == year) & (df['true_date'].dt.month == month)]
        return {"month": month, "year": year, "posts": len(month_df), "month_number": mnumber}
    
    def get_avg_table(self, udf):
        average_persistence = udf["persist"].mean()
        median_persistence = udf["persist"].median()
        average_comments = udf["comments"].mean()
        median_comments = udf["comments"].median()
        average_submissions = udf["submissions"].mean()
        median_submissions = udf["submissions"].median()
        avg_table = {
            "unique_users": len(udf),
            "average_comments": round(average_comments, 3),
            "median_comments": round(median_comments, 3),
            "average_submissions": round(average_submissions, 3),
            "median_submissions": round(median_submissions, 5),
            "average_persistence_days": round(average_persistence, 3),
            "median_persistence_days": round(median_persistence, 3),
        }
        return avg_table

    def render_content(self):
        ds("Reading the dataframes")
        df = pd.read_parquet(self.df_parquet)
        user_df = pd.read_parquet(self.user_df_parquet)
        
        ds("Computing characteristics")
        min_date = user_df["first_post"].min()
        
        ds("Computing characteristics: Filling persistence")
        
        user_df['persist'] = (user_df['last_post'] - user_df['first_post']).dt.days
        
        ds("Computing characteristics: Post lengths")
        average_post_length = df['text'].apply(len).mean()
        median_post_length = df['text'].apply(len).median()
        
        user_df['total_posts'] = user_df['comments'] + user_df['submissions']
        self.user_table = self.get_avg_table(user_df)
        self.user_table["one_post_users"] = len(user_df[user_df["total_posts"] == 1])

        nopu_df = user_df[user_df["total_posts"] > 1]
        self.nopu_table = self.get_avg_table(nopu_df)
        
        u50df = user_df[user_df["total_posts"] >= 50]
        self.u50_table = self.get_avg_table(u50df)
        
        self.posts_table = {
            "total_posts": len(df),
            "first_post": min_date,
            "average_post_length": round(average_post_length, 1),
            "median_post_length": round(median_post_length, 1),
        }
        
        first_date = min_date
        if first_date.month == 12:
            start_month = 1
            start_year = int(first_date.year + 1)
        else:
            start_month =int(first_date.month + 1)
            start_year = int(first_date.year)
        
        end_date = CORPUS_END
        
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

        html = f"<h1>Characteristics of {self.subreddit_name}</h1>"
        html += html_table(self.posts_table, title="posts info", sidebyside=True) 
        html += html_table(self.user_table, title="all_users", sidebyside=True)
        html += html_table(self.nopu_table, title="users_with_more_than_one_post", sidebyside=True) 
        html += html_table(self.u50_table, title="users_with_50_or_more_posts", sidebyside=True)

        ds("working on plot")
        result_list = []
        mnumber = 1
        ticklabels = []
        for year in range(start_year, end_year + 1):
            if year == start_year:
                smonth = start_month
            else:
                smonth = 1
            for month in range(smonth, 13):
                if year == end_year and month > end_month:
                    break
                result_list.append(self.get_month_count(df, month, year, mnumber))
                if month == 1 or month == 7:
                    ticklabels.append([mnumber, f"{year}-{month}"])
                mnumber += 1
        
        post_df = pd.DataFrame(result_list)
        
        html += plot_trajectory(post_df, "month_number", "posts", xstrings=ticklabels,
                                marker_size=self.marker_size)
        self.report = html
        with open(f"{self.working_directory}/{self.subreddit_name}_characteristics_report.html", 'w') as file:
            file.write(html)

if __name__ == '__main__':
    print("starting")
    # jsonfile, subreddit, base_path)
    Tile = SubredditCharacteristicsReport(sys.argv[1], sys.argv[2], sys.argv[3])
    Tile.render_content()