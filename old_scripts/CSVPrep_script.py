print("starting")
import argparse
import pickle
import json
import re, nltk, os, multiprocessing, pickle, math
import numpy as np
import pandas as pd

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



print("done with globals")
class CSVPrep():
    def __init__(self, args):
        import textwrap
        if args.json is not None:
            with open(args.json, 'r') as file:
                config = json.load(file)
            self.csv_path = config["csv_path"] if "csv_path" in config else None
            self.user_data_pkl = config["user_data_pkl"] if "user_data_pkl" in config else None
            self.clean_text = config["clean_text"] if "clean_text" in config else "full"
            self.csv_chunks_to_process = config["csv_chunks_to_process"] if "csv_chunks_to_process" in config else 10
            self.csv_chunk_size = config["csv_chunk_size"] if "csv_chunk_size" in config else 100000
            self.rows_to_display = config["rows_to_display"] if "rows_to_display" in config else 10
            self.add_uid = config["add_uid"] if "add_uid" in config else False
            self.number_of_workers = config["number_of_workers"] if "number_of_workers" in config else 5
            self.output_file = config["output_file"] if "output_file" in config else None
        else:
            self.csv_path = args.csv_path
            self.user_data_pkl = args.user_data_pkl
            self.clean_text = args.clean_text
            self.csv_chunks_to_process = args.csv_chunks_to_process
            self.csv_chunk_size = args.csv_chunk_size
            self.rows_to_display = args.rows_to_display
            self.add_uid = args.add_uid
            self.number_of_workers = args.number_of_workers
            self.output_file = args.output_file
        self.option_names = ["csv_path", "user_data_pkl", "clean_text", "csv_chunks_to_process", "csv_chunk_size", "rows_to_display", "add_uid", "number_of_workers", "output_file"]
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

    def multi_apply(self, chunks, worker, var_dict):
        from multiprocessing import Pool
        cnt = 0
        chunk_count.value = 0
        with Pool(processes=self.number_of_workers) as pool:
            results = pool.starmap(worker, [(chunk, var_dict, len(chunks)) for chunk in chunks])
        return results
    
    def pd_multi_apply(self, df, func, dest, process_name="Processed"):
        nchunks = math.ceil(len(df) / self.csv_chunk_size)
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
    
    def read_csv_to_df(self, csv_path, chunks_to_process=999, chunksize=10**6, prune=True, dtype={}):
        import pandas as pd
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
    
    def extract_csv_name_from_path(self, fpath):
        fname, fext = os.path.splitext(fpath)
        return re.findall("([a-z0-9]*)$", fname)[0]
    
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
        unique_id = self.simple_uid()
        
        user_df = pd.read_pickle(self.user_data_pkl)
        
        types = {"post_id": str,
                 "kind": str,
                 "author": str,
                 "created": str,
                 "title": str,
                 "text": str,
                 "parent_id": str,
                 "num_comments": int}
        df = self.read_csv_to_df(self.csv_path, 
                                 self.csv_chunks_to_process,
                                 self.csv_chunk_size,
                                 True,
                                 dtype=types)
        
        basepath, fext = os.path.splitext(self.csv_path)
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
        
        if self.add_uid:
            path = self.append_uid(f"{basepath}_{self.clean_text}_prep.csv", unique_id)
        else:
            path = f"{basepath}_prep.csv"
        df.to_csv(path, index=False)
            
        self.df_size = len(df)
        results = {
            "df_size": getattr(Tile, "df_size"),
            "parameters": self.get_parameters()
        }
        if self.output_file is not None:
            f = open(self.output_file, "wb")
            pickle.dump(results, f)
            f.close()
            return
        else:
            return results

parser = argparse.ArgumentParser()
parser.add_argument("--csv_path", type=str, default=None)
parser.add_argument("--user_data_pkl", type=str, default=None)
parser.add_argument("--clean_text", type=str, default="full")
parser.add_argument("--csv_chunks_to_process", type=int, default=10)
parser.add_argument("--csv_chunk_size", type=int, default=100000)
parser.add_argument("--rows_to_display", type=int, default=10)
parser.add_argument("--add_uid", type=bool, default=False)
parser.add_argument("--number_of_workers", type=int, default=5)
parser.add_argument("--output_file", type=str, default=None)
parser.add_argument("--json", type=str, default=None)

if __name__ == '__main__':
    print("starting")
    args = parser.parse_args()
    Tile = CSVPrep(args)
    Tile.render_content()