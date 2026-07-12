import urllib.request, os
url = "https://datapilotuploads.blob.core.windows.net/datasets/test_dataset_100k.db?se=2026-07-12T05%3A21Z&sp=racwd&sv=2026-04-06&sr=c&sig=9VswtPnIDJEE8lH90T7in65Msa/ZnYQPh4uRxIAf31w%3D"
dest = "/mnt/uploads/test_dataset_100k.db"
urllib.request.urlretrieve(url, dest)
print(f"OK: {os.path.getsize(dest)} bytes")
