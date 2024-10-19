import nltk, math, time
import numpy as np
import pandas as pd
import multiprocessing, threading
from nltk.lm import Lidstone, MLE
from nltk.util import bigrams, ngrams
from collections import Counter
from typing import *

from utilities import flatten, flatten_and_truncate

global bar_update_seconds

from scipy import linalg, stats

kcount_lock = multiprocessing.Lock()
kchunk_count = multiprocessing.Value('i', 0)

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
        if vdict["truncate_text"]:
            fdist = Counter(flatten_and_truncate(chunk[vdict["text_field"]], vdict["max_len"]))
        else:
            fdist = Counter(flatten(chunk[vdict["text_field"]]))
    with kcount_lock:
        kchunk_count.value += 1
        vdict["display_func"](f"Got fdist for chunk {kchunk_count.value} of {nchunks}")
    return fdist

def kds(txt):
    print(txt)
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
    def __init__(self, leave_unknown=100, max_vocab_size=None, max_discount=.9, 
                 chunk_size=10000, update_seconds=1,
                 number_of_workers=5, text_field="text", gamma=.2, truncate_text=False, max_len=999):
        global bar_update_seconds
        bar_update_seconds = update_seconds
        self.bigram_lm = MLE(order=2)
        self.bigram_fdist = None
        self.unigram_lm = Lidstone(gamma, order=1)
        self.unigram_fdist = None
        self.max_vocab_size = max_vocab_size
        self.leave_unknown = leave_unknown
        self.vocab_size = None
        self.max_discount = max_discount
        self.chunk_size = chunk_size
        self.update_seconds = update_seconds
        self.number_of_workers = number_of_workers
        self.text_field = text_field
        self.vocab = []
        self.discounts = None
        self.alphas = None
        self.cstars = None
        self.truncate_text = truncate_text
        self.max_len = max_len
        return
        
    def __getstate__(self):
        d = {
            "bigram_lm": self.bigram_lm,
            "bigram_fdist": self.bigram_fdist,
            "unigram_lm": self.unigram_lm,
            "unigram_fidst": self.unigram_fdist,
            "vocab_size": self.vocab_size,
            "max_vocab_size": self.max_vocab_size,
            "leave_unknown": self.leave_unknown,
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
            "display_func": kds_spaced,
            "truncate_text": self.truncate_text,
            "max_len": self.max_len
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

        if self.max_vocab_size is not None:
            self.vocab_size = self.max_vocab_size
        elif self.leave_unknown is not None:
            if type(self.leave_unknown) == float:
                self.vocab_size = int(len(fdist) * (1 - self.leave_unknown))
            else:
                self.vocab_size = len(fdist) - self.leave_unknown
        else:
            self.vocab_size = len(fdist)
        mc = fdist.most_common(self.vocab_size)
        self.vocab = [tup[0] for tup in mc]
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
        if not self.truncate_text:
            max_len = 99999
        else:
            max_len = self.max_len
        for n, chunk in enumerate(chunks):
            kds(f"Creating lms for chunk {n} of {nchunks}")
            bgs = [list(bigrams(padded_sents[:max_len])) for padded_sents in chunk[self.text_field].tolist()]
            self.bigram_lm.fit(bgs, self.vocab)
            ugs = [list(ngrams(padded_sents[:max_len], 1)) for padded_sents in chunk[self.text_field].tolist()]
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
        nwords = len(self.vocab) + 1
        aplus = self.vocab + ["<UNK>"]
        for n, w in enumerate(aplus):
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
