print("starting zsts_to_post_csv")
import sys
import json
import json, re, csv
import zstandard


params = ["working_directory", "zst_base", "subreddit_name", "top_level_only"]
print("done with globals")
class SubRedditToCsv():
    def __init__(self, jsonfile):
        with open(jsonfile, 'r') as file:
            config = json.load(file)

        for param in params:
            if param in config:
                setattr(self, param, config[param])
            else:
                setattr(self, param, None)

        self.submissions_zst_path = f"{self.working_directory}/{self.zst_base}_submissions.zst"
        self.comments_zst_path = f"{self.working_directory}/{self.zst_base}_comments.zst"
        self.output_file_name = f"{self.subreddit_name}.csv"
        self.output_path = f"{self.working_directory}/{self.output_file_name}"
        return

    def display_status(self, text):
        print(text)

    def html_table(self, text):
        print(text)

    def process_zst(self, writer, path, kind):
        from datetime import datetime
        total_lines = 0
        created = None
        for line, file_bytes_processed in self.read_lines_zst(path):
            total_lines += 1
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
        self.bad_lines = 0
        
        csvfile = open(self.output_path, 'w', encoding='UTF-8', newline='')
        fieldnames = ["post_id", "kind", 'author', "created", "title", "text", "parent_id", "num_comments"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        self.current_html = ""
        print("Reading submissions\n")
        lines_read = self.process_zst(writer, self.submissions_zst_path, "submission")
        print("Reading comments\n")
        lines_read += self.process_zst(writer, self.comments_zst_path, "comment")
        csvfile.close()

if __name__ == '__main__':
    print("starting")
    Tile = SubRedditToCsv(sys.argv[1])
    Tile.render_content()