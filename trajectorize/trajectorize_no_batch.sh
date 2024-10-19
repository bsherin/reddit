#!/bin/bash

subreddit=$1
snapshot_uid=$2
export SUBREDDIT=$subreddit
export SNAPSHOT_UID=$snapshot_uid

base_script_path="${HOME}/reddit/trajectorize"
cd $base_script_path

./trajectorize_wrapped.sh

# To run this do something like
# ./trajectorize.sh bikewrench 9ccf3