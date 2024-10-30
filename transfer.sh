#!/bin/bash

# globus login

source_folder=$1
source_file=$2
dest_folder=$3 

one_drive_id="930c2fcb-416e-4540-a757-496f86acbe70"
quest_id="d5990400-6d04-11e5-ba46-22000b92c6ec"


~/.conda/envs/first-kernel/bin/globus transfer "${one_drive_id}:/My files/reddit_raw/reddit/${source_folder}/${source_file}" "${quest_id}:/projects/p32275/${dest_folder}/${source_file}"

# ./transfer.sh subreddits2 dndnext_submissions.zst new_uploads
# source folder can also be "uploaded"
