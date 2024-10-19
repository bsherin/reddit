print("starting zsts_to_exp_df")
import sys
import json
import json, re
import pandas as pd
import zstandard

params = ["working_directory", "zst_base", "subreddit_name", "top_level_only"]
print("done with globals")
class SubRedditToCsv():
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
        self.submissions_zst_path = f"{self.working_directory}/{self.subreddit_name}_submissions.zst"
        self.comments_zst_path = f"{self.working_directory}/{self.subreddit_name}_comments.zst"
        self.output_path = f"{self.working_directory}/{self.subreddit_name}_df_exp.parquet"
        return

    def display_status(self, text):
        print(text)

    def html_table(self, text):
        print(text)

    def process_zst(self, path, kind):
        from datetime import datetime
        total_lines = 0
        created = None
        res_list = []
        for line, file_bytes_processed in self.read_lines_zst(path):
            total_lines += 1
            try:
                obj = json.loads(line)
                if (kind == "comment") and (not obj["parent_id"].startswith("t3_")):
                    is_toplevel = False
                else:
                    is_toplevel = True
                created = datetime.utcfromtimestamp(int(obj['created_utc']))
                parent_id = ""
                new_row = {"post_id": obj["id"], "kind": kind, "top_level": is_toplevel, "author": obj["author"], 
                           "created": created, "parent_id": parent_id}
                res_list.append(new_row)
            except (KeyError, json.JSONDecodeError) as err:
                print(self.extract_short_error_message(err, "error reading row"))
                self.bad_lines += 1
        return res_list
    
    def extract_short_error_message(self, e, special_string=None):
        error_type = type(e).__name__
        if special_string is None:
            special_string = "An error occurred of type"
        result = special_string + ": " + error_type
        if len(e.args) > 0:
            result += " " + str(e.args[0])
        return result
    
    def extract_data(self, obj):
        if self.show_all_fields:
            return {field: obj[field] for field in obj.keys()}
        return {field: obj[field] for field in self.desired_fields}
    
    def read_lines_zst(self, file_name):
        with open(file_name, 'rb') as file_handle:
            buffer = ''
            reader = zstandard.ZstdDecompressor(max_window_size=2**31).stream_reader(file_handle)
            while True:
                chunk = self.read_and_decode(reader, 2**27, (2**29) * 2)
    
                if not chunk:
                    break
                lines = (buffer + chunk).split("\n")
    
                for line in lines[:-1]:
                    yield line.strip(), file_handle.tell()
                buffer = lines[-1]
            print("read all lines")
            reader.close()
            
    def read_and_decode(self, reader, chunk_size, max_window_size, previous_chunk=None, bytes_read=0):
        chunk = reader.read(chunk_size)
        bytes_read += chunk_size
        if previous_chunk is not None:
            chunk = previous_chunk + chunk
        try:
            return chunk.decode()
        except UnicodeDecodeError:
            if bytes_read > max_window_size:
                raise UnicodeError(f"Unable to decode frame after reading {bytes_read:,} bytes")
            print(f"Decoding error with {bytes_read:,} bytes, reading another chunk")
            return self.read_and_decode(reader, chunk_size, max_window_size, chunk, bytes_read)
        
    def render_content(self):
        globals()["ds"] = self.display_status
        self.bad_lines = 0
        
        print("Reading submissions\n")
        res_lines = self.process_zst(self.submissions_zst_path, "submission")
        print("Reading comments\n")
        res_lines += self.process_zst(self.comments_zst_path, "comment")
        df = pd.DataFrame(res_lines)
        df.to_parquet(self.output_path)
if __name__ == '__main__':
    print("starting")
    Tile = SubRedditToCsv(sys.argv[1], sys.argv[2], sys.argv[3])
    Tile.render_content()