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

count_lock = multiprocessing.Lock()
chunk_count = multiprocessing.Value('i', 0)

csv_writer = None

def nltk_word_tokenize(txt):
    return word_tokenize(txt)

def flatten(l):
    return [item for sublist in l for item in sublist]

def tokenize_worker(chunk, vdict, nchunks):
    tkizer = nltk_word_tokenize
    try:
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
                raise ex
        with count_lock:
            chunk_count.value += 1
            print(f"Tokenized chunk {chunk_count.value} of {nchunks}")
            for row in chunk:
                csv_writer.writerow(row)
            print(f"wrote chunk {chunk_count.value} to csv")
        return None
    except Exception as e:
        print(f"Worker encountered an error: {e}")
        return None  

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
        self.output_path = f"{self.working_directory}/{self.subreddit_name}_tokenized.csv"
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
        chunk_count.value = 0
        with Pool(processes=self.number_of_workers) as pool:
            results = pool.starmap(worker, [(chunk, var_dict, len(chunks)) for chunk in chunks])
        self.display_status("Got results")
        return
    
    def read_in_chunks(self, filename, chunk_size):
        counter = 0
        clist = []
        with open(filename, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            chunk_data = []
            for n, row in enumerate(reader):
                # if any(header == value for header, value in row.items()):
                #     print(f"got funky row {n}")
                #     print(str(row))
                #     continue
                counter += 1
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
        self.display_status("reading csv")
        start_time = time.time()
        chunks = self.read_in_chunks(self.csv_path, self.chunk_size)
        print(f"got {len(chunks)} chunks")
        
        self.display_status("Creating csv file")
        csv_handle = open(self.output_path, 'w', encoding='UTF-8', newline='')
        fieldnames = ["post_id", "kind", 'author', "title", "text", "parent_id", "num_comments", "seconds", "user_seconds"]
        
        csv_writer = csv.DictWriter(csv_handle, fieldnames=fieldnames)
        csv_writer.writeheader()
        
        self.display_status("tokenizing")
        self.multi_apply(chunks, tokenize_worker, {})
        
        # self.display_status("writing")
        # nchunks = len(chunks)
        # for n, chunk in enumerate(chunks):
        #     self.display_status(f"writing chunk {n} of {nchunks}")
        #     for row in chunk:
        #         csv_writer.writerow(row)
        
        csv_handle.close()
        os.remove(self.csv_path)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Time to tokenize: {elapsed_time} seconds")

if __name__ == '__main__':
    print("starting")
    Tile = CSVPureToTokenizedMultig(sys.argv[1], sys.argv[2], sys.argv[3])
    Tile.render_content()