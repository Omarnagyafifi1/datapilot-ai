#!/bin/bash
URL="https://datapilotuploads.blob.core.windows.net/datasets/test_dataset_100k.db?se=2026-07-12T05%3A21Z&sp=racwd&sv=2026-04-06&sr=c&sig=9VswtPnIDJEE8lH90T7in65Msa/ZnYQPh4uRxIAf31w%3D"
DST="/mnt/uploads/test_dataset_100k.db"
wget -q -O "$DST" "$URL" 2>/dev/null || curl -s -o "$DST" "$URL" 2>/dev/null || python3 -c "import urllib.request; urllib.request.urlretrieve('$URL','$DST')"
echo "Downloaded: $(ls -la $DST | awk '{print $5}') bytes to $DST"
