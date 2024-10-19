print("starting add_true_date_info.py")
import json
import sys
import os
import pandas as pd

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


print("done with globals")
params = ["working_directory", "subreddit_name",]
class LabelTrueDates():
    def __init__(self, jsonfile):
        with open(jsonfile, 'r') as file:
            config = json.load(file)

        for param in params:
            if param in config:
                setattr(self, param, config[param])
            else:
                setattr(self, param, None)

        self.user_df_path = f"{self.working_directory}/{self.subreddit_name}_user_data.parquet"
        self.df_path = f"{self.working_directory}/{self.subreddit_name}_df.parquet" 
        self.output_path = f"{self.working_directory}/{self.subreddit_name}_df_true.parquet"
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
        
        self.display_status("writing")
        
        df.to_parquet(self.output_path)
        os.remove(self.df_path)
        

if __name__ == '__main__':
    print("starting")
    Tile = LabelTrueDates(sys.argv[1])
    Tile.render_content()