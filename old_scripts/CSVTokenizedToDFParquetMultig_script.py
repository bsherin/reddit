print("starting")
import argparse
import pickle
import json
import nltk, math, os, pickle, csv
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
class CSVTokenizedToDFParquetMultig():
    def __init__(self, args):
        import textwrap
        if args.json is not None:
            with open(args.json, 'r') as file:
                config = json.load(file)
            self.csv_path = config["csv_path"] if "csv_path" in config else None
            self.max_lines = config["max_lines"] if "max_lines" in config else 100000
            self.eval_text_column = config["eval_text_column"] if "eval_text_column" in config else True
            self.drop_title = config["drop_title"] if "drop_title" in config else True
            self.chunk_size = config["chunk_size"] if "chunk_size" in config else 100000
            self.number_of_workers = config["number_of_workers"] if "number_of_workers" in config else 6
            self.output_file = config["output_file"] if "output_file" in config else None
        else:
            self.csv_path = args.csv_path
            self.max_lines = args.max_lines
            self.eval_text_column = args.eval_text_column
            self.drop_title = args.drop_title
            self.chunk_size = args.chunk_size
            self.number_of_workers = args.number_of_workers
            self.output_file = args.output_file
        self.option_names = ["csv_path", "max_lines", "eval_text_column", "drop_title", "chunk_size", "number_of_workers", "output_file"]
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
    
    def render_content(self):
        global ds
        ds = self.display_status
        
        ds("reading csv")
        chunks = self.read_in_chunks(self.csv_path, self.chunk_size)
        
        self.display_status("eval-ing or not")
        if self.eval_text_column:
            chunks = self.multi_apply(chunks, eval_worker, {})
        rlist = flatten(chunks)
        
        ds("converting to a dataframe")
        df = pd.DataFrame.from_dict(rlist)
        
        if self.drop_title:
            df.drop(["title"], axis=1, inplace=True)
        
        ds("fixing other column types")
        df["seconds"] = df["seconds"].astype(float)
        df["user_seconds"] = df["user_seconds"].astype(float)
        
        csv_filename, csv_file_extension = os.path.splitext(self.csv_path)
        df_path = f"{csv_filename}_df.parquet"
        
        df.to_parquet(df_path)
        
        print("wrote file")

parser = argparse.ArgumentParser()
parser.add_argument("--csv_path", type=str, default=None)
parser.add_argument("--max_lines", type=int, default=100000)
parser.add_argument("--eval_text_column", type=bool, default=True)
parser.add_argument("--drop_title", type=bool, default=True)
parser.add_argument("--chunk_size", type=int, default=100000)
parser.add_argument("--number_of_workers", type=int, default=6)
parser.add_argument("--output_file", type=str, default=None)
parser.add_argument("--json", type=str, default=None)

if __name__ == '__main__':
    print("starting")
    args = parser.parse_args()
    Tile = CSVTokenizedToDFParquetMultig(args)
    Tile.render_content()