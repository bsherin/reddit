
seed=1
base_unique_id=$(date +%s%N | md5sum | head -c 5)
unique_id="${base_unique_id}_exp_${seed}"
echo "Extended Unique ID: $unique_id"