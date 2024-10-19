print("starting clean_and_add_seconds.py")
import json
import re, os, multiprocessing, math
import sys
import pandas as pd
import numpy as np

min_date = None
min_values_df = None

count_lock = multiprocessing.Lock()
chunk_count = multiprocessing.Value('i', 0)

pattern = r"[^a-zA-Z\s]|\bhttps?\S+\b"
def full_clean(text):
    return re.sub(pattern, '', str(text), flags = re.IGNORECASE)

url_pattern = r"\bhttps?\S+\b"
def url_clean(text):
    return re.sub(url_pattern, '', str(text), flags = re.IGNORECASE)
    
def clean_worker(chunk, vdict, nchunks):
    mask = (
        (chunk["author"] != "[deleted]") & 
        (chunk["author"] != "AutoModerator")
    )
    chunk = chunk[mask]
    with count_lock:
        chunk_count.value += 1
        ds(f"cleaned chunk {chunk_count.value} of {nchunks}")
    return chunk

def delta_seconds(row):
    delta = row["date"] - min_date
    return int(delta.total_seconds())

def compute_user_seconds(row):
    delta = row["date"] - user_df.loc[row["author"], "first_post"]
    return int(delta.total_seconds())

def generic_pd_worker(chunk, vdict, nchunks):
    chunk[vdict["dest"]] = chunk.apply(vdict["func"], 1)
    with count_lock:
        chunk_count.value += 1
        ds(f"{vdict['process_name']} chunk {chunk_count.value} of {nchunks}")
    return chunk

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)

print("done with globals")
params = ["working_directory", "subreddit_name", "clean_text", "chunk_size", "number_of_workers"]
class CSVPrep():
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

        self.df_exp_path = f"{self.working_directory}/{self.subreddit_name}_df_exp.parquet"
        self.user_data_path = f"{self.working_directory}/{self.subreddit_name}_user_data.parquet"
        self.output_path = f"{self.working_directory}/{self.subreddit_name}_df_exp_seconds.parquet"
        return

    def display_status(self, text):
        print(text)

    def html_table(self, text):
        print(text)

    def multi_apply(self, chunks, worker, var_dict):
        from multiprocessing import Pool
        cnt = 0
        chunk_count.value = 0
        with Pool(processes=self.number_of_workers) as pool:
            results = pool.starmap(worker, [(chunk, var_dict, len(chunks)) for chunk in chunks])
        return results
    
    def pd_multi_apply(self, df, func, dest, process_name="Processed"):
        nchunks = math.ceil(len(df) / self.chunk_size)
        chunks = np.array_split(df, nchunks)
        clist = self.multi_apply(chunks, generic_pd_worker, 
                                 {"dest": dest, "process_name": process_name, "func": func})
        if len(chunks) > 1:
            return pd.concat(clist)
        else:
            return clist[0]
    
    def opt_requirements(self, opt_name):
        reqs = {
            "stop_list": lambda: self.remove_stopwords,
        }
        result = True
        if opt_name in reqs:
            result = reqs[opt_name]()
        return result
    
    def modify_options(self):
        new_options = []
        for opt in self.options:
            opt["visible"] = self.opt_requirements(opt["name"])
            new_options.append(opt)
        return new_options
    
    def simple_uid(self):
        import string, random
        alphabet = string.ascii_lowercase + string.digits
        return ''.join(random.choices(alphabet, k=8))
    
    def append_uid(self, path, unique_id):
        fname, fext = os.path.splitext(path)
        return f"{fname}_{unique_id}{fext}"
    
    def pd_cnt_apply(self, ldf, source_field, func, modval, subtext=""):
        cnt = 0
        total = len(ldf)
        def ct_func(src):
            nonlocal cnt
            cnt += 1
            return func(src)
        if source_field is None:
            return ldf.apply(ct_func, 1)
        return ldf.apply(lambda row: ct_func(row[source_field]), 1)
    
    def render_content(self):
        global ds
        global min_date
        global min_values_df
        global user_df
        
        ds = self.display_status
        
        user_df = load_pickle_or_parquet(self.user_data_path)
        
        df = pd.read_parquet(self.df_exp_path)
        
        ds("Converting date column to datetime")
        df['date'] = pd.to_datetime(df['created'])
        ds('Getting min date')
        min_date = user_df["first_post"].min()

        ds("cleaning")
        mask = (
            (df["author"] != "[deleted]") & 
            (df["author"] != "AutoModerator")
        )
        df = df[mask]
        
        ds("Filling seconds column")
        df = self.pd_multi_apply(df, delta_seconds, "seconds", "filling seconds")
        
        ds("Adding user seconds: writing user seconds")
        df = self.pd_multi_apply(df, compute_user_seconds, "user_seconds", "Got user seconds")
        
        df.drop(["created", "date"], axis=1, inplace=True)
        
        ds("saving to CSV")
        
        df.to_parquet(self.output_path, index=False)
        os.remove(self.df_exp_path)

if __name__ == '__main__':
    print("starting")
    Tile = CSVPrep(sys.argv[1], sys.argv[2], sys.argv[3])
    Tile.render_content()