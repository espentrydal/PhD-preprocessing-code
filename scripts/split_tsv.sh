#!/bin/bash

# Default split size
split_size=10

# Parse command line options
while getopts "s:" opt; do
  case $opt in
  s)
    split_size=$OPTARG
    ;;
  \?)
    echo "Invalid option: -$OPTARG"
    exit 1
    ;;
  esac
done

# Shift to get the input file argument
shift $((OPTIND - 1))

# Check if an argument is provided
if [ $# -eq 0 ]; then
  echo "Usage: $0 [-s lines_per_split] <input_file.tsv>"
  echo "  -s: number of lines per split (default: 10)"
  exit 1
fi

# Input file
input_file="$1"

# Check if the input file exists
if [ ! -f "$input_file" ]; then
  echo "Error: File $input_file not found."
  exit 1
fi

# Get the base name of the input file (without extension)
base_name=$(basename "$input_file" .tsv)

# Extract the header
header=$(head -n 1 "$input_file")

# Split the file, excluding the header
tail -n +2 "$input_file" | split -l "$split_size" - "${base_name}_temp_"

# Counter for naming files
count=1

# Add header to each file and rename
for file in "${base_name}"_temp_*; do
  echo "$header" | cat - "$file" >"${base_name}_${count}.tsv"
  rm "$file"
  ((count++))
done

echo "Split complete. Files are named ${base_name}_1.tsv, ${base_name}_2.tsv, etc."
