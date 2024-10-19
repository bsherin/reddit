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
        (chunk["author"] != "AutoModerator") & 
        (chunk["text"].str.contains("[deleted]", regex=False) == False) &
        (chunk["text"].str.contains("[removed]", regex=False) == False) &
        (chunk["text"] != "nan")
    )
    chunk = chunk[mask]
    if Tile.clean_text == "full":
        chunk["text"] = chunk.apply(lambda row: full_clean(row["text"]), 1)
    elif Tile.clean_text == "urls_only":
        chunk["text"] = chunk.apply(lambda row: url_clean(row["text"]), 1)
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
    def __init__(self, jsonfile):
        with open(jsonfile, 'r') as file:
            config = json.load(file)

        for param in params:
            if param in config:
                setattr(self, param, config[param])
            else:
                setattr(self, param, None)

        self.csv_path = f"{self.working_directory}/{self.subreddit_name}.csv"
        self.user_data_path = f"{self.working_directory}/{self.subreddit_name}_user_data.parquet"
        output_file_name = f"{self.subreddit_name}_prep.csv"
        self.output_path = f"{self.working_directory}/{output_file_name}"
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
    
    def read_csv_to_df(self, csv_path, chunksize=10**6, dtype={}):
        clist = []
        counter = 0
    
        def count_lines(filename):
            with open(filename, 'r') as f:
                return sum(1 for line in f)
    
        self.display_status("Getting CSV size")
        nlines = count_lines(csv_path) - 1
        nchunks = nlines // chunksize
        def dinfo(text, cnt):
            self.display_status(f"{text} chunk {counter} of {nchunks}")
        self.display_status(f"CSV has {nchunks} total chunks. Reading")
        chunk_list = []
        with pd.read_csv(csv_path, chunksize=chunksize, dtype=dtype, index_col=False) as reader:
            for chunk in reader:
                chunk_list.append(chunk)
    
        self.display_status("cleaning")
        clist = self.multi_apply(chunk_list, clean_worker, {})
        df = pd.concat(clist, ignore_index=True)
        return df
    
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
        
        types = {"post_id": str,
                 "kind": str,
                 "author": str,
                 "created": str,
                 "title": str,
                 "text": str,
                 "parent_id": str,
                 "num_comments": int}
        df = self.read_csv_to_df(self.csv_path, 
                                 self.chunk_size,
                                 dtype=types)
        
        ds("Converting date column to datetime")
        df['date'] = pd.to_datetime(df['created'])
        ds('Getting min date')
        min_date = user_df["first_post"].min()
        
        ds("Filling seconds column")
        df = self.pd_multi_apply(df, delta_seconds, "seconds", "filling seconds")
        
        ds("Adding user seconds: writing user seconds")
        df = self.pd_multi_apply(df, compute_user_seconds, "user_seconds", "Got user seconds")
        
        df.drop(["created", "date"], axis=1, inplace=True)
        
        ds("saving to CSV")
        
        df.to_csv(self.output_path, index=False)
        os.remove(self.csv_path)

if __name__ == '__main__':
    print("starting")
    Tile = CSVPrep(sys.argv[1])
    Tile.render_content()