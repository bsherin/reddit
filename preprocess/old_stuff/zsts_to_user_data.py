print("starting zsts_to_user_data.py")
import pickle
import json
import sys
import zstandard, os, json, re, csv, copy
import pandas as pd

blank_user = {"author": None, "first_post": None, "last_post": None, 
              "submissions": 0, "comments": 0, "top_level_comments": 0}

ignore_users = ["[deleted]", "AutoModerator"]

def ds(text):
    print(text)

params = ["working_directory", "zst_base", "subreddit_name"]
print("done with globals")
class SubRedditToUserData():
    def __init__(self, jsonfile):
        import textwrap
        with open(jsonfile, 'r') as file:
            config = json.load(file)
        
        for param in params:
            if param in config:
                setattr(self, param, config[param])
            else:
                setattr(self, param, None)
        self.submissions_zst_path = f"{self.working_directory}/{self.zst_base}_submissions.zst"
        self.comments_zst_path = f"{self.working_directory}/{self.zst_base}_comments.zst"
        self.output_file_name = f"{self.subreddit_name}_user_data.parquet"
        self.output_path = f"{self.working_directory}/{self.output_file_name}"
        return

    def display_status(self, text):
        print(text)

    def html_table(self, text):
        print(text)

    def process_zst(self, path, kind):
        from datetime import datetime
        file_size = os.stat(path).st_size
        total_lines = 0
        created = None
        for line, file_bytes_processed in self.read_lines_zst(path):
            total_lines += 1
            try:
                obj = json.loads(line)
                author = obj["author"]
                if author in ignore_users:
                    continue
                if author not in self.user_data:
                    self.user_data[author] = copy.copy(blank_user)
                    self.user_data[author]["author"] = author
                urow = self.user_data[author]
                if kind == "submission":
                    urow["submissions"] += 1
                if kind == "comment":
                    urow["comments"] += 1
                    if obj["parent_id"].startswith("t3_"):
                        urow["top_level_comments"] += 1
                created = datetime.utcfromtimestamp(int(obj['created_utc']))
                if urow["first_post"] is None or created < urow["first_post"]:
                    urow["first_post"] = created
                if urow["last_post"] is None or created > urow["last_post"]:
                    urow["last_post"] = created
            except (KeyError, json.JSONDecodeError) as err:
                print(self.extract_short_error_message(err, "error reading row"))
                self.bad_lines += 1
        return total_lines
    
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
            log.info(f"Decoding error with {bytes_read:,} bytes, reading another chunk")
            return read_and_decode(reader, chunk_size, max_window_size, chunk, bytes_read)
        
    def render_content(self):
        global ds
        ds = self.display_status
        create = None
        self.bad_lines = 0
        
        self.user_data = {}
        ds("Reading submissions")
        lines_read = self.process_zst(self.submissions_zst_path, "submission")
        ds("Reading comments")
        lines_read += self.process_zst(self.comments_zst_path, "comment")
        
        
        df = pd.DataFrame.from_dict(self.user_data.values())
        df.set_index("author", inplace=True)
        self.df = df
        self.author_list = list(self.user_data.keys())

        ds("Writing file")
        df.to_parquet(self.output_path)

if __name__ == '__main__':
    print("starting")
    Tile = SubRedditToUserData(sys.argv[1])
    Tile.render_content()