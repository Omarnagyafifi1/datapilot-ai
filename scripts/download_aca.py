import os, urllib.request
url = "https://datapilotuploads.blob.core.windows.net/datasets/test_dataset_100k.db?se=2026-07-12T05%3A21Z&sp=racwd&sv=2026-04-06&sr=c&sig=9VswtPnIDJEE8lH90T7in65Msa/ZnYQPh4uRxIAf31w%3D"
# Try Azure Files first
dest = "/mnt/uploads/test_dataset_100k.db"
if os.path.isdir("/mnt/uploads"):
    urllib.request.urlretrieve(url, dest)
    print(f"Downloaded to Azure Files: {dest} ({os.path.getsize(dest)} bytes)")
else:
    dest2 = "/app/backend/data/test_dataset_100k.db"
    urllib.request.urlretrieve(url, dest2)
    print(f"Downloaded to local: {dest2} ({os.path.getsize(dest2)} bytes)")
print("DONE")
