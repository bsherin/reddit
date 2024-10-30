#!/bin/bash

# globus login

source_path=$1
dest_path=$2

one_drive_id="930c2fcb-416e-4540-a757-496f86acbe70"
quest_id="d5990400-6d04-11e5-ba46-22000b92c6ec"



globus transfer "${one_drive_id}:/My files/${dest_path}" "${quest_id}:/projects/p32275/${dest_path}"