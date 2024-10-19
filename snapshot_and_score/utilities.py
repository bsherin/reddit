def flatten(l):
    return [item for sublist in l for item in sublist]

def flatten_and_truncate(l, maxlen):
    return [item for sublist in l for item in sublist[:maxlen]]
