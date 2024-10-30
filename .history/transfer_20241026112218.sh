#!/bin/bash

# globus login

source_file=$1
dest_folder=$2 

one_drive_id="930c2fcb-416e-4540-a757-496f86acbe70"
quest_id="d5990400-6d04-11e5-ba46-22000b92c6ec"

# source folder can also be "uploaded"
"~/.conda/envs/first-kernel/bin/globus" transfer "${one_drive_id}:/My files/reddit_raw/reddit/subreddits2/${source_file}" "${quest_id}:/projects/p32275/${dest_folder}/${source_file}"

# ./transfer.sh dndnext_submissions.zst new_uploads

