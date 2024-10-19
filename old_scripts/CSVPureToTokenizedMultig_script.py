print("starting")
import argparse
import pickle
import json
import nltk, re, os, csv
import pandas as pd
import time
import multiprocessing
from nltk import sent_tokenize
from nltk.tokenize import word_tokenize
from nltk.lm.preprocessing import pad_both_ends, flatten

count_lock = multiprocessing.Lock()
chunk_count = multiprocessing.Value('i', 0)

def nltk_word_tokenize(txt):
    return word_tokenize(txt)

def flatten(l):
    return [item for sublist in l for item in sublist]

def tokenize_worker(chunk, vdict, nchunks):
    tkizer = nltk_word_tokenize
    for row in chunk:
        try:
            if Tile.sent_tokenize:
                if Tile.pad_and_flatten:
                    row["text"] = list(flatten([pad_both_ends(tkizer(sent), 2) for sent in sent_tokenize(row["text"])]))
                else:
                    row["text"] = [tkizer(sent) for sent in sent_tokenize(row["text"])]
            else:
                row["text"] = tkizer(row["text"])
        except Exception as ex:
            print("error handling row " + str(row))
            print(handle_exception(ex))
            raise Exception
    # chunk = None
    with count_lock:
        chunk_count.value += 1
        Tile.display_status(f"Wrote chunk {chunk_count.value} of {nchunks}")
    return chunk

def handle_exception(ex, special_string=None):
    if special_string is None:
        template = "<pre>An exception of type {0} occured. Arguments:\n{1!r}</pre>"
    else:
        template = "<pre>" + special_string + "\n" + "An exception of type {0} occurred. Arguments:\n{1!r}</pre>"
    error_string = template.format(type(ex).__name__, ex.args)
    return error_string


print("done with globals")
class CSVPureToTokenizedMultig():
    def __init__(self, args):
        import textwrap
        if args.json is not None:
            with open(args.json, 'r') as file:
                config = json.load(file)
            self.csv_path = config["csv_path"] if "csv_path" in config else None
            self.max_lines = config["max_lines"] if "max_lines" in config else 100000
            self.sent_tokenize = config["sent_tokenize"] if "sent_tokenize" in config else False
            self.pad_and_flatten = config["pad_and_flatten"] if "pad_and_flatten" in config else False
            self.tokenizer = config["tokenizer"] if "tokenizer" in config else None
            self.add_uid = config["add_uid"] if "add_uid" in config else False
            self.chunk_size = config["chunk_size"] if "chunk_size" in config else 100000
            self.number_of_workers = config["number_of_workers"] if "number_of_workers" in config else 6
            self.output_file = config["output_file"] if "output_file" in config else None
        else:
            self.csv_path = args.csv_path
            self.max_lines = args.max_lines
            self.sent_tokenize = args.sent_tokenize
            self.pad_and_flatten = args.pad_and_flatten
            self.tokenizer = args.tokenizer
            self.add_uid = args.add_uid
            self.chunk_size = args.chunk_size
            self.number_of_workers = args.number_of_workers
            self.output_file = args.output_file
        self.option_names = ["csv_path", "max_lines", "sent_tokenize", "pad_and_flatten", "tokenizer", "add_uid", "chunk_size", "number_of_workers", "output_file"]
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
        self.display_status("Got results")
        return results
    
    def read_in_chunks(self, filename, chunk_size):
        counter = 0
        clist = []
        with open(filename, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            chunk_data = []
            for n, row in enumerate(reader):
                if any(header == value for header, value in row.items()):
                    print(f"got funky row {n}")
                    print(str(row))
                    continue
                counter += 1
                if counter > self.max_lines:
                    break;
                if len(chunk_data) < chunk_size:
                    chunk_data.append(row)
                else:
                    clist.append(chunk_data)
                    chunk_data = [row]
            if chunk_data:
                clist.append(chunk_data)
        return clist
    
    def simple_uid(self):
        import string, random
        alphabet = string.ascii_lowercase + string.digits
        return ''.join(random.choices(alphabet, k=8))
    
    def append_uid(self, path, unique_id):
        fname, fext = os.path.splitext(path)
        return f"{fname}_{unique_id}{fext}"
    def render_content(self):
        global csv_writer
        unique_id = self.simple_uid()
        csv_filename, csv_file_extension = os.path.splitext(self.csv_path)
        tokenized_str = "sent_tokenized" if self.sent_tokenize else "tokenized"
        pf_str = "pf_" if self.pad_and_flatten and self.sent_tokenize else ""
        csv_out_path = f"{csv_filename}_{pf_str}{tokenized_str}.csv"
        
        self.display_status("reading csv")
        start_time = time.time()
        chunks = self.read_in_chunks(self.csv_path, self.chunk_size)
        
        if self.add_uid:
            csv_out_path = self.append_uid(csv_out_path, unique_id)
        
        self.display_status("Creating csv file")
        csv_handle = open(csv_out_path, 'w', encoding='UTF-8', newline='')
        fieldnames = ["post_id", "kind", 'author', "title", "text", "parent_id", "num_comments", "seconds", "user_seconds"]
        
        csv_writer = csv.DictWriter(csv_handle, fieldnames=fieldnames)
        csv_writer.writeheader()
        
        self.display_status("tokenizing")
        chunks = self.multi_apply(chunks, tokenize_worker, {})
        
        self.display_status("writing")
        nchunks = len(chunks)
        for n, chunk in enumerate(chunks):
            self.display_status(f"writing chunk {n} of {nchunks}")
            for row in chunk:
                csv_writer.writerow(row)
        
        csv_handle.close()
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time to tokenize: {elapsed_time} seconds")

parser = argparse.ArgumentParser()
parser.add_argument("--csv_path", type=str, default=None)
parser.add_argument("--max_lines", type=int, default=100000)
parser.add_argument("--sent_tokenize", type=bool, default=False)
parser.add_argument("--pad_and_flatten", type=bool, default=False)
parser.add_argument("--tokenizer", type=str, default=None)
parser.add_argument("--add_uid", type=bool, default=False)
parser.add_argument("--chunk_size", type=int, default=100000)
parser.add_argument("--number_of_workers", type=int, default=6)
parser.add_argument("--output_file", type=str, default=None)
parser.add_argument("--json", type=str, default=None)

if __name__ == '__main__':
    print("starting")
    args = parser.parse_args()
    Tile = CSVPureToTokenizedMultig(args)
    Tile.render_content()