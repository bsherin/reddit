print("starting eval_and_convert_to_parquet.py")
import json
import os, csv, sys
import pandas as pd
import multiprocessing

count_lock = multiprocessing.Lock()
chunk_count = multiprocessing.Value('i', 0)

def flatten(l):
    return [item for sublist in l for item in sublist]

def eval_worker(chunk, vdict, nchunks):
    new_chunk = []
    for row in chunk:
        try:
            row["text"] = eval(row["text"])
            new_chunk.append(row)
        except Exception as ex:
            print("got exception evaluating row " + str(row))
            print(handle_exception(ex))
            raise Exception
    with count_lock:
        chunk_count.value += 1
        Tile.display_status(f"evaled chunk {chunk_count.value} of {nchunks}")
    return new_chunk

def handle_exception(ex, special_string=None):
    if special_string is None:
        template = "<pre>An exception of type {0} occured. Arguments:\n{1!r}</pre>"
    else:
        template = "<pre>" + special_string + "\n" + "An exception of type {0} occurred. Arguments:\n{1!r}</pre>"
    error_string = template.format(type(ex).__name__, ex.args)
    return error_string



print("done with globals")
params = ["working_directory", "subreddit_name", "chunk_size", "number_of_workers"]
class CSVTokenizedToDFParquetMultig():
    def __init__(self, jsonfile):
        with open(jsonfile, 'r') as file:
            config = json.load(file)

        for param in params:
            if param in config:
                setattr(self, param, config[param])
            else:
                setattr(self, param, None)

        self.csv_path = f"{self.working_directory}/{self.subreddit_name}_tokenized.csv"
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

    def multi_apply(self, chunks, worker, var_dict):
        from multiprocessing import Pool
        cnt = 0
        chunk_count.value = 0
        with Pool(processes=self.number_of_workers) as pool:
            results = pool.starmap(worker, [(chunk, var_dict, len(chunks)) for chunk in chunks])
        return results
    
    def read_in_chunks(self, filename, chunk_size):
        counter = 0
        clist = []
        with open(filename, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            chunk_data = []
            for row in reader:
                counter += 1
                if len(chunk_data) < chunk_size:
                    chunk_data.append(row)
                else:
                    clist.append(chunk_data)
                    chunk_data = [row]
            if chunk_data:
                clist.append(chunk_data)
        return clist
    
    def render_content(self):
        global ds
        ds = self.display_status
        
        ds("reading csv")
        chunks = self.read_in_chunks(self.csv_path, self.chunk_size)
        
        self.display_status("eval-ing")
        chunks = self.multi_apply(chunks, eval_worker, {})
        rlist = flatten(chunks)
        
        ds("converting to a dataframe")
        df = pd.DataFrame.from_dict(rlist)
        
        df.drop(["title"], axis=1, inplace=True)
        
        ds("fixing other column types")
        df["seconds"] = df["seconds"].astype(float)
        df["user_seconds"] = df["user_seconds"].astype(float)
        
        df.to_parquet(self.output_path)
        os.remove(self.csv_path)
        print("wrote file")

if __name__ == '__main__':
    print("starting")
    Tile = CSVTokenizedToDFParquetMultig(sys.argv[1])
    Tile.render_content()