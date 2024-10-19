print("starting")
import argparse
import pickle
import json
import nltk, math, time
import os, re
import numpy as np
import pandas as pd
import random
import multiprocessing, threading
from nltk.lm import Lidstone, MLE
from nltk.util import bigrams, ngrams
from collections import defaultdict
from sklearn.model_selection import ParameterGrid
from sklearn.model_selection import train_test_split
import math

base_lm = None

status_stub = "blah"
print("status_stub is set " + status_stub)

count_lock = multiprocessing.Lock()
chunk_count = multiprocessing.Value('i', 0)

def days_to_secs(days):
    return days * 86400

def flatten(l):
    return [item for sublist in l for item in sublist]

class KatzBigramLM:
    def __init__(self, vocab_size, default_discount, max_discount, gamma=.2):
        self.bigram_lm = MLE(order=2)
        self.bigram_fdist = None
        self.unigram_lm = Lidstone(gamma, order=1)
        self.unigram_fdist = None
        self.vocab_size = vocab_size
        self.default_discount = default_discount
        self.max_discount = max_discount
        self.vocab = []
        self.discounts = None
        self.alphas = None
        self.Ns = None
        return
    
    def create_vocabulary(self, df):
        ds("creating vocabulary")
        fdist = Tile.df_to_fdist(df)
        mc = fdist.most_common(self.vocab_size)
        self.vocab = [tup[0] for tup in mc]
        if "<UNK>" not in self.vocab:
            self.vocab.append("<UNK>")
        print(f"***got vocab of size {len(self.vocab)}***")
        return
        
    def create_bigram_lm(self, df):
        def cfd_to_fdist(cfd):
            fd = nltk.FreqDist()
            for condition in cfd.conditions():
                for word, freq in cfd[condition].items():
                    fd[(condition[0], word)] += freq
            return fd
        nchunks = math.ceil(len(df) / Tile.chunk_size)
        chunks = np.array_split(df, nchunks)
        for n, chunk in enumerate(chunks):
            ds(f"Creating bigram_lm chunk {n} of {nchunks}")
            bgs = [list(bigrams(padded_sents)) for padded_sents in chunk["text"].tolist()]
            self.bigram_lm.fit(bgs, self.vocab)
        self.bigram_fdist = cfd_to_fdist(self.bigram_lm.counts[2])
        
    def create_unigram_lm(self, df):
        nchunks = math.ceil(len(df) / Tile.chunk_size)
        chunks = np.array_split(df, nchunks)
        for n, chunk in enumerate(chunks):
            ds(f"Creating unigram chunk {n} of {nchunks}")
            ugs = [list(ngrams(padded_sents, 1)) for padded_sents in chunk["text"].tolist()]
            self.unigram_lm.fit(ugs, self.vocab)
        self.unigram_fdist = self.unigram_lm.counts[1]
        
    def compute_Ns(self):
        ds("computing Ns")
        self.Ns = nltk.FreqDist(self.bigram_fdist.values())
        
    def compute_discounts(self):
        ds("computing discounts")
        discounts = {}
        for k, cnt in self.bigram_fdist.items():
            if self.Ns[cnt + 1] == 0 or self.Ns[cnt] == 0:
                discounts[k] = self.default_discount
            else:
                c_star = (cnt + 1) * self.Ns[cnt + 1] / self.Ns[cnt]
                disc = min(c_star / cnt, self.max_discount)
                discounts[k] = disc
            if discounts[k] == 0:
                print(f"*** got a zero discount for k={str(k)} ***")
        self.discounts = discounts
    
    def compute_word_alpha(self, word):
        fd = self.bigram_lm.counts[[word]]
        s_numerator = sum(self.score((word, k)) for k, cnt in fd.items() if cnt > 0)
        s_denom = 1 - sum(self.unigram_lm.score(wtup[0]) for wtup in self.bigram_lm.counts[2][word].keys())
        alpha = (1 - s_numerator) / s_denom
        return alpha
    
    def compute_alphas(self):
        ds("computing alphas")
        self.alphas = {}
        nwords = len(self.vocab)
        for n, w in enumerate(self.vocab):
            self.alphas[w] = self.compute_word_alpha(w)
            ds_spaced(f"Got alpha for word {n} of {nwords}")
            
    def get_alpha(self, word):
        if word not in self.alphas:
            self.alphas[word] = self.compute_word_alpha(word)
        return self.alphas[word]
    
    def fit(self, df):
        self.create_vocabulary(df)
        print("got vocab")
        self.create_bigram_lm(df)
        self.create_unigram_lm(df)
        self.compute_Ns()
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
                Tile.error_info = {"vocab": self.vocab, "alphas": self.alphas, "bg": bg}
                raise RuntimeError(f"{str(self.unk_token(bg[0]))} is not in self.alphas, bg[0] was {bg[0]}")
    
    def entropy(self, bg_list):
        if len(bg_list) == 0:
            return 0
        lsum = 0
        for bg in bg_list:
            score = self.score(bg)
            if score <= 0:
                raise RuntimeError(f"Got score of {score} in entropy for bg {str(bg)}")
            lsum += math.log(score)
        return - 1 * lsum / len(bg_list)
    
    def avg_chunk_entropy(self, chunk):
        entropies = [self.entropy(list(bigrams(padded_sents))) for padded_sents in chunk["text"]]
        return np.mean(entropies)
        
    def avg_chunk_perplexity(self, chunk, given_avg_entropy=None):
        if given_avg_entropy is None:
            avg_entropy = self.avg_chunk_entropy(chunk)
        else:
            avg_entropy = given_avg_entropy
        return 2 ** avg_entropy

def ds(txt):
    global status_stub
    print(f"In ds with status_stub {status_stub} and txt {txt}")
    Tile.display_status(status_stub + txt)
    return

def df_to_fdist_worker(chunk, vdict, nchunks):
    if chunk is None:
        fdist = None
    else:
        fdist = nltk.FreqDist(flatten(chunk["text"]))
    with count_lock:
        chunk_count.value += 1
        ds_spaced(f"Got fdist for chunk {chunk_count.value} of {nchunks}")
    return fdist

def has_none(alist):
    for item in alist:
        if item is None:
            return True
    return False

def average_list_of_lists(lofl):
    nlists = len(lofl)
    llen = len(lofl[0])
    avg_list = []
    for c in range(llen):
        tot = sum([lis[c] for lis in lofl]) / nlists
        avg_list.append(tot)
    return avg_list

def ds_spaced(txt):
    global ds_timer
    global last_ds_time
    def do_it(txt):
        ds(txt)
        return 
    if "last_ds_time" not in globals():
        ds_timer = None
        last_ds_time = time.time()
        ds(txt)
    else:
        if ds_timer is not None:
            ds_timer.cancel()
        current_time = time.time()
        if (current_time - last_ds_time) > Tile.bar_update_seconds:
            ds(txt)
            last_ds_time = current_time
        else:
            ds_timer = threading.Timer(Tile.bar_update_seconds, lambda : do_it(txt))
        return


print("done with globals")
class NgramModelTesterBaseSample():
    def __init__(self, args):
        import textwrap
        fname = f"/projects/p32275/{args.json}"
        if args.json is not None:
            with open(fname, 'r') as file:
                config = json.load(file)
            self.df_pickle = config["df_pickle"] if "df_pickle" in config else None
            self.user_df_pkl = config["user_df_pkl"] if "user_df_pkl" in config else None
            self.user_base_fraction = config["user_base_fraction"] if "user_base_fraction" in config else 0.75
            self.param_grid = config["param_grid"] if "param_grid" in config else "{'vocab_size': [10000, 50000, 100000],  'default_discount': [0.1, 0.3, 0.5, 0.7, 0.9],  'max_discount': [0.8, 0.9, 1.0]}"
            self.base_start_week = config["base_start_week"] if "base_start_week" in config else None
            self.base_end_week = config["base_end_week"] if "base_end_week" in config else None
            self.number_of_workers = config["number_of_workers"] if "number_of_workers" in config else 5
            self.bar_update_seconds = config["bar_update_seconds"] if "bar_update_seconds" in config else 1
            self.chunk_size = config["chunk_size"] if "chunk_size" in config else 10000
            self.output_file = config["output_file"] if "output_file" in config else None
        else:
            self.df_pickle = args.df_pickle
            self.user_df_pkl = args.user_df_pkl
            self.user_base_fraction = args.user_base_fraction
            self.param_grid = args.param_grid
            self.base_start_week = args.base_start_week
            self.base_end_week = args.base_end_week
            self.number_of_workers = args.number_of_workers
            self.bar_update_seconds = args.bar_update_seconds
            self.chunk_size = args.chunk_size
            self.output_file = args.output_file
        self.option_names = ["df_pickle", "user_df_pkl", "user_base_fraction", "param_grid", "base_start_week", "base_end_week", "number_of_workers", "bar_update_seconds", "chunk_size", "output_file"]
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

    def evaluate_model(self, params, df, validation_df):
        model = KatzBigramLM(params['vocab_size'], params['default_discount'], params["max_discount"])
        model.fit(df)
        entropies = []
        avg_entropy = model.avg_chunk_entropy(validation_df)
        avg_perplexity = model.avg_chunk_perplexity(None, avg_entropy)
        vsize = len(model.vocab)
        return {"actual_vocab_size": vsize, "entropy": avg_entropy, "perplexity": avg_perplexity}
    
    def multi_apply(self, chunks, worker, var_dict):
        from multiprocessing import Pool
        cnt = 0
        chunk_count.value = 0
        with Pool(processes=self.number_of_workers) as pool:
            results = pool.starmap(worker, [(chunk, var_dict, len(chunks)) for chunk in chunks])
        return results
    
    def df_to_fdist(self, df):
        nchunks = math.ceil(len(df) / self.chunk_size)
        chunks = np.array_split(df, nchunks)
        fdists = self.multi_apply(chunks, df_to_fdist_worker, {})
        cfdist = nltk.FreqDist()
        for fdist in fdists:
            if fdist is not None:
                for word, freq in fdist.items():
                    cfdist[word] += freq
        return cfdist
    
    def prune_users_on_posts(self, pudf, min_posts):
        pudf["total_posts"] = pudf.apply(lambda row: row["submissions"] + row["top_level_comments"], 1)
        return pudf[pudf["total_posts"] >= min_posts]
    
    def prune_users_on_persist(self, pudf, min_persist):
        def persist(row):
            delta = row["last_post"] - row["first_post"]
            return int(delta.total_seconds())
        pudf["persist"] = pudf.apply(persist, 1)
        return pudf[pudf["persist"] >= min_persist]
    def render_content(self):
        global status_stub
        import copy
        self.display_status("reading")
        self.error_info = {}
        
        df = pd.read_pickle(self.df_pickle)
        
        user_df = pd.read_pickle(self.user_df_pkl)
                                 
        ds("Pruning users before sampling")
        pudf = user_df
        min_persist = days_to_secs(7 * self.base_end_week)
        pudf = self.prune_users_on_persist(pudf, min_persist)
        print(f"number of authors after persist pruning {len(pudf)}")
        
        print(f"length before pruning is {len(df)}")
        authors_to_keep = pudf.index.to_list()
        df = df[df["author"].isin(authors_to_keep)]
        print(f"length after persist pruning is {len(df)}")
        print(f"number of authors after pruning {len(pudf)}")
        
        
        self.failed_samples_list_list = []
        self.first_failed_sample_day_list = []
        nbase = int(self.user_base_fraction * len(authors_to_keep))
        random.shuffle(authors_to_keep)
        base_users = authors_to_keep[:nbase]
        base_df = df[df["author"].isin(base_users)]
        
        base_start_seconds = days_to_secs(self.base_start_week * 7)
        base_end_seconds = days_to_secs(self.base_end_week * 7)
        base_df = base_df[base_df["user_seconds"].between(base_start_seconds, base_end_seconds)]
        
        print(f"number of posts in base_df {len(base_df)}")
        
        train_df, validation_df = train_test_split(base_df, test_size=0.2, random_state=42)
        
        ntraining_posts = len(train_df)
        nvalidation_posts = len(validation_df)
        print(f"training_posts: {ntraining_posts} validation_posts: {nvalidation_posts}")
        
        param_grid = eval(self.param_grid)
        self.results_list = []
        rlist_temp = []
        blank_score = {"actual_vocab_size": 0, "entropy": 0, "perplexity": 0}
        for params in ParameterGrid(param_grid):
            params_plus = copy.copy(params)
            params_plus.update(blank_score)
            rlist_temp.append(params_plus)
            rlist_temp_df = pd.DataFrame(rlist_temp)
            status_stub = str(rlist_temp_df.round(2))
            print(f"assigned status_stub {status_stub}")
            ds("starting")
            score_dict = self.evaluate_model(params, train_df, validation_df)
            params_plus.update(score_dict)
            rlist_temp_df = pd.DataFrame(rlist_temp)
            status_stub = str(rlist_temp_df.round(2))
            ds("got result")
            self.results_list.append(params_plus)
        self.results_df = pd.DataFrame(self.results_list)
        self.results_df_rounded = self.results_df.round(2)
        html = f"<div>training_posts: {ntraining_posts} validation_posts: {nvalidation_posts}</div>"
        html += str(self.results_df_rounded)
        results = {
            "results_list": getattr(Tile, "results_list"),
            "results_df": getattr(Tile, "results_df"),
            "results_df_rounded": getattr(Tile, "results_df_rounded"),
            "error_info": getattr(Tile, "error_info"),
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
parser.add_argument("--df_pickle", type=str, default=None)
parser.add_argument("--user_df_pkl", type=str, default=None)
parser.add_argument("--user_base_fraction", type=str, default=0.75)
parser.add_argument("--param_grid", type=str, default="{'vocab_size': [10000, 50000, 100000],  'default_discount': [0.1, 0.3, 0.5, 0.7, 0.9],  'max_discount': [0.8, 0.9, 1.0]}")
parser.add_argument("--base_start_week", type=int, default=None)
parser.add_argument("--base_end_week", type=int, default=None)
parser.add_argument("--number_of_workers", type=int, default=5)
parser.add_argument("--bar_update_seconds", type=int, default=1)
parser.add_argument("--chunk_size", type=int, default=10000)
parser.add_argument("--output_file", type=str, default=None)
parser.add_argument("--json", type=str, default=None)

if __name__ == '__main__':
    print("starting")
    args = parser.parse_args()
    Tile = NgramModelTesterBaseSample(args)
    Tile.render_content()