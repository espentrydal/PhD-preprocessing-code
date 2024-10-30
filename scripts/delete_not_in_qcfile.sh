#!/bin/bash

# First, let's make sure QCpassed.txt exists
if [ ! -f QCpassed.txt ]; then
  echo "Error: QCpassed.txt not found"
  exit 1
fi

# Find all directories in the current directory
# For each directory, check if its name is NOT in QCpassed.txt
# If it's not in the file, delete the directory
find . -maxdepth 1 -type d ! -name "." | while read dir; do
  dirname=$(basename "$dir")
  if ! grep -qFx "$dirname" QCpassed.txt; then
    echo "Deleting $dir"
    rm -rf "$dir"
  fi
done

echo "Deletion process completed."
