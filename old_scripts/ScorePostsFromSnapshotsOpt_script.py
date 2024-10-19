print("starting")
import argparse
import pickle
import json
import pickle
import os
import pandas as pd
from nltk.util import bigrams
from concurrent.futures import ThreadPoolExecutor

kb_model = None

month_list = ["January", "February", "March", "April", "May", "June", "July", "August",
             "September", "October", "November", "December"]

class DuplicateIndices(Exception): 
    def __init__(self, df_name):
        super().__init__(df_name)
        self.df_name = df_name
    pass

def process_month(year, month, smonth, emonth, text_df, score_df, snapshot_folder, uid):
    print(f"Processing year {year} month {month}")
    month_df = text_df[(text_df['true_date'].dt.year == year) & (text_df['true_date'].dt.month == month)]
    
    with open(f"{snapshot_folder}/snapshots/{month_name(month)}-{year}", "rb") as f:
        snapshot_dict = pickle.load(f)
    
    kb_model = KatzBigramLM(50, .9)
    kb_model.__setstate__(snapshot_dict["lm_dict"])
    used_posts = snapshot_dict["post_ids"]
    month_df = month_df[~month_df.index.isin(used_posts)]
    
    results = month_df['text'].apply(score_function, kb_model=kb_model)
    score_df.loc[results.index, uid] = results

def check_for_dupes(df, df_name):
    duplicates = df.index.duplicated()
    duplicate_rows = df[duplicates]
    if len(duplicate_rows) == 0:
        return False
    else:
        Tile.dupes = duplicate_rows
        raise DuplicateIndices(df_name)

def month_number(month_name):
    return 1 + month_list.index(month_name)

def month_name(month_number):
    return month_list[month_number - 1]

def score_function(txt, kb_model):
    return kb_model.entropy(list(bigrams(txt)))

def load_pickle_or_parquet(path):
    fname, ext = os.path.splitext(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    else:
        return pd.read_pickle(path)
    
import nltk, math, time
import numpy as np
import pandas as pd
import multiprocessing, threading
from nltk.lm import Lidstone, MLE
from nltk.util import bigrams, ngrams
from collections import Counter
from typing import *

global bar_update_seconds

from scipy import linalg, stats

kcount_lock = multiprocessing.Lock()
kchunk_count = multiprocessing.Value('i', 0)

def ds(text):
    print(text)
    return

def get_cstars(freqdist, p_value=0.05, allow_fail=True, default_p0=None):
    confidence_level = stats.norm.ppf(1.0 - (p_value / 2.0))

    freqs_of_freqs = nltk.FreqDist(freqdist.values())
    freqs_keys = np.array(sorted(freqs_of_freqs.keys()))

    p0 = freqs_of_freqs[1] / freqs_of_freqs.N() if 1 in freqs_keys else (default_p0 or 1.0 / (freqs_of_freqs.N() + 1))


    i = np.r_[0, freqs_keys[:-1]]
    k = np.r_[freqs_keys[1:], 2 * freqs_keys[-1] - i[-1]]
    z = 2 * np.array([freqs_of_freqs[key] / freqs_of_freqs.N() for key in freqs_keys]) / (k - i)
    
    slope, intercept = np.linalg.lstsq(np.c_[np.log(freqs_keys), np.ones_like(freqs_keys)], np.log(z), rcond=None)[0]

    if slope > -1.0 and allow_fail:
        raise RuntimeWarning("In SGT, linear regression slope is > -1.0.")

    r_smoothed = nltk.FreqDist()
    use_y = False
    for r in freqs_keys:
        y = (r + 1) * np.exp(slope * np.log(r + 1) + intercept) / np.exp(slope * np.log(r) + intercept)
        if r + 1 not in freqs_of_freqs:
            if not use_y:
                if allow_fail:
                    raise RuntimeWarning("In SGT, unobserved count before smoothing threshold.")
            use_y = True

        if use_y:
            r_smoothed[r] = y
        else:
            estim = (r + 1) * freqs_of_freqs[r + 1] / freqs_of_freqs[r]

            nr = float(freqs_of_freqs[r])
            nr1 = float(freqs_of_freqs[r + 1])
            width = confidence_level * np.sqrt((r + 1) ** 2 * (nr1 / nr**2) * (1.0 + (nr1 / nr)))

            if abs(estim - y) > width:
                r_smoothed[r] = estim
            else:
                use_y = True
                r_smoothed[r] = y

    return r_smoothed

def df_to_fdist_worker(chunk, vdict, nchunks):
    if chunk is None:
        fdist = None
    else:
        fdist = Counter(flatten(chunk[vdict["text_field"]]))
    with kcount_lock:
        kchunk_count.value += 1
        vdict["display_func"](f"Got fdist for chunk {kchunk_count.value} of {nchunks}")
    return fdist

def kds(txt):
    if hasattr(Tile, "status_stub"):
        Tile.display_status(Tile.status_stub + txt)
    else:
        Tile.display_status(txt)
    return

def kds_spaced(txt):
    global kds_timer
    global klast_ds_time
    def do_it(txt):
        kds(txt)
        return 
    if "klast_ds_time" not in globals():
        kds_timer = None
        klast_ds_time = time.time()
        kds(txt)
    else:
        if kds_timer is not None:
            kds_timer.cancel()
        current_time = time.time()
        if (current_time - klast_ds_time) > bar_update_seconds:
            kds(txt)
            klast_ds_time = current_time
        else:
            kds_timer = threading.Timer(bar_update_seconds, lambda : do_it(txt))
        return
    
class KatzBigramLM:
    def __init__(self, vocab_size, max_discount, 
                 chunk_size=10000, update_seconds=1, 
                 number_of_workers=5, text_field="text", gamma=.2):
        global bar_update_seconds
        bar_update_seconds = update_seconds
        self.bigram_lm = MLE(order=2)
        self.bigram_fdist = None
        self.unigram_lm = Lidstone(gamma, order=1)
        self.unigram_fdist = None
        self.vocab_size = vocab_size
        self.max_discount = max_discount
        self.chunk_size = chunk_size
        self.update_seconds = update_seconds
        self.number_of_workers = number_of_workers
        self.text_field = text_field
        self.vocab = []
        self.discounts = None
        self.alphas = None
        self.cstars = None
        return
        
    def __getstate__(self):
        d = {
            "bigram_lm": self.bigram_lm,
            "bigram_fdist": self.bigram_fdist,
            "unigram_lm": self.unigram_lm,
            "unigram_fidst": self.unigram_fdist,
            "vocab_size": self.vocab_size,
            "max_discount": self.max_discount,
            "chunk_size": self.chunk_size,
            "update_seconds": self.update_seconds,
            "number_workers": self.number_of_workers,
            "text_field": self.text_field,
            "vocab": self.vocab,
            "discounts": self.discounts,
            "alphas": self.alphas,
            "cstars": self.cstars
        }
        return d
          
    def __setstate__(self, d):
         for k, v in d.items():
             setattr(self, k, v)

    def df_to_fdist(self, df):
        nchunks = math.ceil(len(df) / self.chunk_size)
        chunks = np.array_split(df, nchunks)
        fdists = self.multi_apply(chunks, df_to_fdist_worker, {
            "text_field": self.text_field,
            "display_func": kds_spaced
        })
        cfdist = nltk.FreqDist()
        for fdist in fdists:
            if fdist is not None:
                for word, freq in fdist.items():
                    cfdist[word] += freq
        return cfdist

    def multi_apply(self, chunks, worker, var_dict):
        from multiprocessing import Pool
        cnt = 0
        kchunk_count.value = 0
        with Pool(processes=self.number_of_workers) as pool:
            results = pool.starmap(worker, [(chunk, var_dict, len(chunks)) for chunk in chunks])
        return results
        
    def create_vocabulary(self, df):
        kds("creating vocabulary")
        fdist = self.df_to_fdist(df)
        mc = fdist.most_common(self.vocab_size)
        self.vocab = [tup[0] for tup in mc]
        if "<UNK>" not in self.vocab:
            self.vocab.append("<UNK>")
        print(f"***got vocab of size {len(self.vocab)}***")
        return

    def create_lms(self, df):
        def cfd_to_fdist(cfd):
            fd = nltk.FreqDist()
            for condition in cfd.conditions():
                for word, freq in cfd[condition].items():
                    fd[(condition[0], word)] += freq
            return fd
        nchunks = math.ceil(len(df) / self.chunk_size)
        chunks = np.array_split(df, nchunks)
        for n, chunk in enumerate(chunks):
            kds(f"Creating lms for chunk {n} of {nchunks}")
            bgs = [list(bigrams(padded_sents)) for padded_sents in chunk[self.text_field].tolist()]
            self.bigram_lm.fit(bgs, self.vocab)
            ugs = [list(ngrams(padded_sents, 1)) for padded_sents in chunk[self.text_field].tolist()]
            self.unigram_lm.fit(ugs, self.vocab)
        self.bigram_fdist = cfd_to_fdist(self.bigram_lm.counts[2])
        self.unigram_fdist = self.unigram_lm.counts[1]
        
    def compute_cstars(self):
        self.cstars = get_cstars(self.bigram_fdist)
        
    def compute_discounts(self):
        kds("computing discounts")
        discounts = {}
        for k, cnt in self.bigram_fdist.items():
            disc = min(self.cstars[cnt] / cnt, self.max_discount)
            discounts[k] = disc
            if discounts[k] == 0:
                print(f"*** got a zero discount for k={str(k)} ***")
        self.discounts = discounts

    def compute_word_alpha(self, word):
        try:
            fd = self.bigram_lm.counts[[word]]
            s_numerator = sum(self.score((word, k)) for k, cnt in fd.items() if cnt > 0)
            s_denom = sum(self.unigram_lm.score(wtup[0]) for wtup in self.bigram_lm.counts[2][(word,)].keys())
            alpha = (1 - s_numerator) / s_denom
        except ZeroDivisionError:
            print(f"got division by zero error for word {word}")
            print(f"count keys are {str(list(self.bigram_lm.counts[2][(word,)].keys()))}")
            return .1
        return alpha
    
    def compute_alphas(self):
        kds("computing alphas")
        self.alphas = {}
        nwords = len(self.vocab)
        for n, w in enumerate(self.vocab):
            self.alphas[w] = self.compute_word_alpha(w)
            kds_spaced(f"Got alpha for word {n} of {nwords}")
            
    def get_alpha(self, word):
        return self.alphas[word]
    
    def fit(self, df):
        self.create_vocabulary(df)
        print("got vocab")
        self.create_lms(df)
        self.compute_cstars()
        self.compute_discounts()
        self.compute_alphas()
        print("got alphas")
        return
    
    def unk_bg(self, bg):
        bgl = list(bg)
        bgl[0] = self.unk_token(bgl[0])
        bgl[1] = self.unk_token(bgl[1])
        return tuple(bgl)
    
    def unk_token(self, token):
        result = token if token in self.vocab else "<UNK>"
        return result
    
    def score(self, bg):
        bscore = self.bigram_lm.score(bg[1], [bg[0]])
        if not bscore == 0:
            return self.discounts[self.unk_bg(bg)] * bscore
        try:
            return self.alphas[self.unk_token(bg[0])] * self.unigram_lm.score(self.unk_token(bg[1]))
        except:
            if self.unk_token(bg[0]) in self.alphas:
                raise RuntimeError(f"{str(self.unk_token(bg[0]))} is in self.alphas, bg[0] was {bg[0]}")
            else:
                raise RuntimeError(f"{str(self.unk_token(bg[0]))} is not in self.alphas, bg[0] was {bg[0]}")

    def entropy(self, bg_list):
        if len(bg_list) == 0:
            return 0
        raw_ent = self.raw_entropy(bg_list)
        return raw_ent / len(bg_list)
    
    def raw_entropy(self, bg_list):
        if len(bg_list) == 0:
            return 0
        return -1 * sum([math.log(self.score(bg), 2) for bg in bg_list])
    
    def avg_chunk_entropy(self, chunk):
        entropies = [self.entropy(list(bigrams(padded_sents))) for padded_sents in chunk["text"]]
        return np.mean(entropies)
    
    def evaluate_chunk(self, chunk):
        n_bgs = 0
        post_entropies = []
        post_entropies_per_bg = []
        post_perplexities_from_raw_entropy = []
        post_perplexities_from_entropy_per_bg = []
        new_chunk = [psents for psents in chunk["text"] if len(psents) > 0]
        nposts = len(new_chunk)
        for padded_sents in new_chunk:
            bg_list = list(bigrams(padded_sents))
            raw_entropy = self.raw_entropy(bg_list)
            post_entropies.append(raw_entropy)
            post_entropies_per_bg.append(raw_entropy / len(bg_list))
            post_perplexities_from_raw_entropy.append(0)
            post_perplexities_from_entropy_per_bg.append(0)
            n_bgs += len(bg_list)
            
        raw_total_entropy = sum(post_entropies)
        entropy_per_bg_from_raw_total = raw_total_entropy / n_bgs
        entropy_per_post_from_post_entropies_per_bg =sum(post_entropies_per_bg) / nposts
        
        return [entropy_per_bg_from_raw_total, 
                entropy_per_post_from_post_entropies_per_bg]
        
    def avg_chunk_perplexity(self, chunk, given_avg_entropy=None):
        if given_avg_entropy is None:
            avg_entropy = self.avg_chunk_entropy(chunk)
        else:
            avg_entropy = given_avg_entropy
        return 2 ** avg_entropy


print("done with globals")
class ScorePostsFromSnapshotsOpt():
    def __init__(self, args):
        import textwrap
        if args.json is not None:
            with open(args.json, 'r') as file:
                config = json.load(file)
            self.snapshot_folder = config["snapshot_folder"] if "snapshot_folder" in config else None
            self.text_df_file = config["text_df_file"] if "text_df_file" in config else None
            self.score_df_file = config["score_df_file"] if "score_df_file" in config else None
            self.overwrite_score_df = config["overwrite_score_df"] if "overwrite_score_df" in config else False
            self.new_score_file_name = config["new_score_file_name"] if "new_score_file_name" in config else "score.parquet"
            self.output_file = config["output_file"] if "output_file" in config else None
        else:
            self.snapshot_folder = args.snapshot_folder
            self.text_df_file = args.text_df_file
            self.score_df_file = args.score_df_file
            self.overwrite_score_df = args.overwrite_score_df
            self.new_score_file_name = args.new_score_file_name
            self.output_file = args.output_file
        self.option_names = ["snapshot_folder", "text_df_file", "score_df_file", "overwrite_score_df", "new_score_file_name", "output_file"]
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

    def pull_param_vals(self):
        param_df = pd.read_csv(f"{self.snapshot_folder}/parameters.txt", sep=":\t", names=["key", "value"], index_col="key")
        keys = param_df.index.tolist()
        for key in keys:
            setattr(self, key, param_df.loc[key].value)
        return
    
    def opt_requirements(self, opt_name):
        reqs = {
            "new_score_file_name": lambda: not self.overwrite_score_df,
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
        
    def render_content(self):
        ds("Getting snapshot params")
        global kb_model
        self.pull_param_vals()
        ds("Reading text df")
        try:
            text_df = load_pickle_or_parquet(self.text_df_file)
            if "post_id" in text_df.columns:
                text_df.set_index('post_id', inplace=True)
            ds("removing duplicates")
            text_df = text_df[~text_df.index.duplicated(keep='first')]
            ds("Reading score df")
            score_df = load_pickle_or_parquet(self.score_df_file)
            if "post_id" in score_df.columns:
                score_df.set_index("post_id", inplace=True)
            ds("removing duplicates")
            score_df = score_df[~score_df.index.duplicated(keep='first')]
            score_df[self.uid] = -999
            
            smonth_num = month_number(self.start_month)
            emonth_num = month_number(self.end_month)
            self.start_year = int(self.start_year)
            self.end_year = int(self.end_year)
        
            text_df = text_df[(text_df['true_date'].dt.year >= self.start_year) & 
                (text_df['true_date'].dt.year <= self.end_year)]
            ds("filtered text_df, creating exeuctor")
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for year in range(self.start_year, self.end_year + 1):
                    ds(f"starting year {year}")
                    smonth = smonth_num if year == self.start_year else 1
                    emonth = emonth_num if year == self.end_year else 12
            
                    for month in range(smonth, emonth + 1):
                        futures.append(executor.submit(process_month, year, month, smonth, emonth, 
                                                       text_df, score_df, self.snapshot_folder, self.uid))
                
                for future in futures:
                    future.result()
                    
            ds("writing the file")
            if self.overwrite_score_df:
                output_path = self.score_df_file
            else:
                output_dir = os.path.dirname(self.score_df_file)
                output_path = f"{output_dir}/{self.new_score_file_name}"
            
            score_df.to_parquet(output_path)
            return "done"
        
        except DuplicateIndices as e:
            html = f"Lengh of dupicates in {e} is {len(self.dupes)}<br>"
            html += self.html_table(self.dupes.head())
        results = {
            "dupes": getattr(Tile, "dupes"),
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
parser.add_argument("--snapshot_folder", type=str, default=None)
parser.add_argument("--text_df_file", type=str, default=None)
parser.add_argument("--score_df_file", type=str, default=None)
parser.add_argument("--overwrite_score_df", type=bool, default=False)
parser.add_argument("--new_score_file_name", type=str, default="score.parquet")
parser.add_argument("--output_file", type=str, default=None)
parser.add_argument("--json", type=str, default=None)

if __name__ == '__main__':
    print("starting")
    args = parser.parse_args()
    Tile = ScorePostsFromSnapshotsOpt(args)
    Tile.render_content()