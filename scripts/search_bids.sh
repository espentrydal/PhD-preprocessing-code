#!/bin/bash

# Check if minimum number of arguments are provided
if [ "$#" -lt 3 ]; then
  echo "Usage: $0 -dt <subfolder1> [subfolder2] ... [subfolderN] <bids_directory>"
  exit 1
fi

# Process arguments
subfolders=()
while [[ $# -gt 1 ]]; do
  case "$1" in
  -dt)
    shift
    while [[ $# -gt 1 && ! "$1" =~ ^- ]]; do
      subfolders+=("$1")
      shift
    done
    ;;
  *)
    echo "Error: Unknown option $1"
    echo "Usage: $0 -dt <subfolder1> [subfolder2] ... [subfolderN] <bids_directory>"
    exit 1
    ;;
  esac
done

# Last argument is the BIDS directory to search
if [ ${#subfolders[@]} -eq 0 ]; then
  echo "Error: At least one subfolder must be specified after -dt"
  echo "Usage: $0 -dt <subfolder1> [subfolder2] ... [subfolderN] <bids_directory>"
  exit 1
fi

search_dir="$1"

# Create secure temporary file
tmp_file=$(mktemp)
trap 'rm -f "$tmp_file"' EXIT

# Write header to output file
echo -e "participant_id\tsession_id" >"$tmp_file"

# Function to check if all specified subfolders exist
check_subfolders() {
  local ses_dir="$1"
  for subfolder in "${subfolders[@]}"; do
    if [ ! -d "$ses_dir/$subfolder" ]; then
      return 1
    fi
  done
  return 0
}

# Search for matching directories and write to output file
find "$search_dir" -type d -path "*/sub-*/ses-*" | while read -r ses_path; do
  if check_subfolders "$ses_path"; then
    sub_id=$(basename "$(dirname "$ses_path")")
    ses_id=$(basename "$ses_path")
    echo -e "$sub_id\t$ses_id" >>"$tmp_file"
  fi
done

# Create final output file securely
sort -u "$tmp_file"
