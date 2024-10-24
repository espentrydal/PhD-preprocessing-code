#!/bin/bash

# Run with nohup ./run_clinica_batch.sh > all_processing.log 2>&1 &

for i in {1..119}
do
    echo "Processing file $i..."
    clinica run dwi-preprocessing-using-t1 -np 10 \
    -tsv ./adni/data/dwi/${i}_dwi_subjects.tsv \
    -wd ./tmp${i} \
    ./adni/bids ./adni/caps 2>&1 | tee dwi-preprocessing-${i}.log
    
    echo "Finished processing file $i."
    echo "------------------------"
done

echo "All processing complete."
