print("starting")
import argparse
import pickle
import json
import zstandard, os, json, re, csv


print("done with globals")
class SubRedditToCsv():
    def __init__(self, args):
        import textwrap
        if args.json is not None:
            with open(args.json, 'r') as file:
                config = json.load(file)
            self.submissions_zst_path = config["submissions_zst_path"] if "submissions_zst_path" in config else None
            self.comments_zst_path = config["comments_zst_path"] if "comments_zst_path" in config else None
            self.output_directory = config["output_directory"] if "output_directory" in config else None
            self.output_file_name = config["output_file_name"] if "output_file_name" in config else None
            self.max_lines_to_process = config["max_lines_to_process"] if "max_lines_to_process" in config else 1000
            self.top_level_only = config["top_level_only"] if "top_level_only" in config else False
            self.output_file = config["output_file"] if "output_file" in config else None
        else:
            self.submissions_zst_path = args.submissions_zst_path
            self.comments_zst_path = args.comments_zst_path
            self.output_directory = args.output_directory
            self.output_file_name = args.output_file_name
            self.max_lines_to_process = args.max_lines_to_process
            self.top_level_only = args.top_level_only
            self.output_file = args.output_file
        self.option_names = ["submissions_zst_path", "comments_zst_path", "output_directory", "output_file_name", "max_lines_to_process", "top_level_only", "output_file"]
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

    def process_zst(self, writer, path, kind):
        from datetime import datetime
        file_size = os.stat(path).st_size
        total_lines = 0
        created = None
        for line, file_bytes_processed in self.read_lines_zst(path):
            total_lines += 1
            if total_lines > self.max_lines_to_process:
                break
            try:
                obj = json.loads(line)
                if self.top_level_only and (kind == "comment") and (not obj["parent_id"].startswith("t3_")):
                    continue
                created = datetime.utcfromtimestamp(int(obj['created_utc']))
                parent_id = ""
                num_comments = 0
                if "selftext" in obj:
                    text = obj["selftext"]
                elif "body" in obj:
                    text = obj["body"]
                else:
                    text = ""
                if kind == "submission":
                    title = obj["title"]
                    num_comments = obj["num_comments"]
                else:
                    title = ""
                    if "parent_id" in obj:
                        parent_id = obj["parent_id"]
                    num_comments = 0
                text = re.sub("[\r\n]", "", text)
                new_row = {"post_id": obj["id"], "kind": kind, "author": obj["author"], 
                           "created": created, "title": title, "text": text, "parent_id": parent_id, 
                           "num_comments": num_comments}
                writer.writerow(new_row)
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
        globals()["ds"] = self.display_status
        create = None
        self.bad_lines = 0
        
        output_path = f"{self.output_directory}/{self.output_file_name}"
        
        #if os.path.exists(output_path):
            #raise FileExistsError
        csvfile = open(output_path, 'w', encoding='UTF-8', newline='')
        fieldnames = ["post_id", "kind", 'author', "created", "title", "text", "parent_id", "num_comments"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        self.current_html = ""
        print("Reading submissions\n")
        lines_read = self.process_zst(writer, self.submissions_zst_path, "submission")
        print("Reading comments\n")
        lines_read += self.process_zst(writer, self.comments_zst_path, "comment")
        csvfile.close()
        results = {
            "all_fields": getattr(Tile, "all_fields"),
            "data_table": getattr(Tile, "data_table"),
            "parameters": self.get_parameters()
        }

parser = argparse.ArgumentParser()
parser.add_argument("--submissions_zst_path", type=str, default=None)
parser.add_argument("--comments_zst_path", type=str, default=None)
parser.add_argument("--output_directory", type=str, default=None)
parser.add_argument("--output_file_name", type=str, default=None)
parser.add_argument("--max_lines_to_process", type=int, default=1000)
parser.add_argument("--top_level_only", type=bool, default=False)
parser.add_argument("--output_file", type=str, default=None)
parser.add_argument("--json", type=str, default=None)

if __name__ == '__main__':
    print("starting")
    args = parser.parse_args()
    Tile = SubRedditToCsv(args)
    Tile.render_content()