print("starting tokenize_cleaned_csv.py")
import json
import os, csv
import sys
import pandas as pd
import time
import multiprocessing
from nltk import sent_tokenize
from nltk.tokenize import word_tokenize
from nltk.lm.preprocessing import pad_both_ends, flatten
import dask.dataframe as dd

count_lock = multiprocessing.Lock()
chunk_count = multiprocessing.Value('i', 0)

csv_writer = None

def tokenize_pad_and_flatten(txt):
    return list(flatten([pad_both_ends(word_tokenize(sent), 2) for sent in sent_tokenize(txt)]))

def flatten(l):
    return [item for sublist in l for item in sublist]


def process_chunk_dask(df_chunk):
    df_chunk['text'] = df_chunk['text'].apply(tokenize_pad_and_flatten)
    return df_chunk

def handle_exception(ex, special_string=None):
    if special_string is None:
        template = "<pre>An exception of type {0} occured. Arguments:\n{1!r}</pre>"
    else:
        template = "<pre>" + special_string + "\n" + "An exception of type {0} occurred. Arguments:\n{1!r}</pre>"
    error_string = template.format(type(ex).__name__, ex.args)
    return error_string


print("done with globals")
params = ["working_directory", "subreddit_name", "chunk_size", "number_of_workers", "sent_tokenize", "pad_and_flatten"]
class CSVPureToTokenizedMultig():
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

        self.csv_path = f"{self.working_directory}/{self.subreddit_name}_prep.csv"
        self.output_path = f"{self.working_directory}/{self.subreddit_name}_df.parquet"
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
    
    def append_uid(self, path, unique_id):
        fname, fext = os.path.splitext(path)
        return f"{fname}_{unique_id}{fext}"
    
    def render_content(self):
        global csv_writer        
        self.display_status("reading to dask and processing")

        start_time = time.time()
        ddf = dd.read_csv(self.csv_path, blocksize=self.chunk_size)
        ddf = ddf.map_partitions(process_chunk_dask)
        ddf.to_parquet(self.output_path)

        os.remove(self.csv_path)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time to tokenize: {elapsed_time} seconds")

if __name__ == '__main__':
    print("starting")
    Tile = CSVPureToTokenizedMultig(sys.argv[1], sys.argv[2], sys.argv[3])
    Tile.render_content()