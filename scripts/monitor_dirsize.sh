#!/bin/bash

directory="$1" # The directory to monitor
interval=5     # Interval in seconds

if [ -z "$directory" ]; then
  echo "Usage: $0 <directory>"
  exit 1
fi

highest_bytes=0

to_bytes() {
  local size=$1
  local unit=${size: -1}
  local number=${size:0:-1}
  case $unit in
  K) echo "$((${number%.*} * 1024))" ;;
  M) echo "$((${number%.*} * 1024 * 1024))" ;;
  G) echo "$((${number%.*} * 1024 * 1024 * 1024))" ;;
  T) echo "$((${number%.*} * 1024 * 1024 * 1024 * 1024))" ;;
  *) echo "$number" ;;
  esac
}

while true; do
  current_readable=$(du -hs "$directory" | awk '{print $1}')
  current_bytes=$(to_bytes "$current_readable")

  if [ $current_bytes -gt $highest_bytes ]; then
    highest_bytes=$current_bytes
    highest_readable=$current_readable
  fi

  clear
  echo "Directory: $directory"
  echo "Current size: $current_readable"
  echo "Highest size: $highest_readable"

  sleep $interval
done
