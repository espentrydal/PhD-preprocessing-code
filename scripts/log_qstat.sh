#!/bin/bash
JOB=$1
LOGFILE="job_${JOB}_usage.log"
TMPFILE="job_${JOB}_usage.tmp"

qstat -j "$JOB" | grep "usage" | tee -a "$LOGFILE"

if [ "$(stat -c%s "$LOGFILE")" -gt 10485760 ]; then
  tail -c 5242880 "$LOGFILE" >"$TMPFILE"
  mv "$TMPFILE" "$LOGFILE"
fi
