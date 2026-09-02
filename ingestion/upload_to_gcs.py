"""
Upload every CSV from the data folder into the GCS landing zone.
"""

from pathlib import Path
from google.cloud import storage

# --- config ---
BUCKET_NAME = "ae-supply-mehdi-landing"
PREFIX = "raw"    # the folder inside the bucket
DATA_DIR = Path(__file__).resolve().parents[1]/"data_generation"/"data"

def main():
    #1. connect to GCS
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)

    #2 find every .csv file in DATA_DIR
    csv_files = list(DATA_DIR.glob("*.csv"))

    #3. Upload each one 
    for csv_path in csv_files:
        blob_name = f"{PREFIX}/{csv_path.name}"
        blob = bucket.blob(blob_name)  
        blob.upload_from_filename(str(csv_path))
        print(f"upload {csv_path.name} -> gs://{BUCKET_NAME}/{blob_name}")

if __name__ == "__main__" : 
    main()