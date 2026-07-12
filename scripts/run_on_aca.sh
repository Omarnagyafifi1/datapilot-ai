#!/bin/bash
set -e
# Use local container storage (Azure Files/SMB doesn't support SQLite locking)
SRC=/mnt/uploads
DST=/app/backend/data
LOG=$DST/gen_azure_run.log
echo "[$(date)] Starting generation..." > $LOG
python $SRC/gen_azure.py $DST 0.5 >> $LOG 2>&1
echo "[$(date)] Generation complete" >> $LOG
