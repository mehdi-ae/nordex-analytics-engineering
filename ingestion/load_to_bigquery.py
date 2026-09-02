"""
Load every CSV in the GCS landing zone into the BigQuery raw dataset,
every column as STRING (a faithful raw layer, cleaning will happen later)
"""
from google.cloud import bigquery, storage

# --- config ---
PROJECT = "ae-supply-mehdi"
DATASET = "raw"
BUCKET_NAME = "ae-supply-mehdi-landing"
PREFIX = "raw"

# the 11 source files -> table names
TABLES = [
    "products", "sites", "carriers", "customers", 
    "orders", "order_lines", 
    "fulfillments", "inventory_snapshots", "inbound_receipts",
    "shipments", "finance_ledger",
]

def string_schema_from_gcs(bucket_name, blob_name):
    """
    Read only the header row of a CSV in GCS, return an all-STRING schema.
    """
    gcs=storage.Client()
    blob = gcs.bucket(bucket_name).blob(blob_name)
    #download only the first chunk of bytes - enough for the header, not the whole file
    header_bytes = blob.download_as_bytes(start=0, end=65536)
    header_line = header_bytes.decode("utf-8").splitlines()[0]
    columns = header_line.split(",")
    return [bigquery.SchemaField(col.strip(), "STRING") for col in columns]

def main():
    client = bigquery.Client(project=PROJECT)

    for table in TABLES:
        uri = f"gs://{BUCKET_NAME}/{PREFIX}/{table}.csv"
        table_id = f"{PROJECT}.{DATASET}.{table}"

        #build an all-STRING schema from the file's header in GCS
        schema = string_schema_from_gcs(BUCKET_NAME, f"{PREFIX}/{table}.csv")

        
        # build the load configuration
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV, 
            skip_leading_rows=1,  #skip the header
            schema=schema,        # 
            write_disposition="WRITE_TRUNCATE"  # replace table each run(idempotent)
        )

        # start the load job and wait for it to finish
        load_job = client.load_table_from_uri(uri, table_id, job_config=job_config)
        load_job.result()  #blocks until done

        #confirm 
        table_obj = client.get_table(table_id)
        print(f"loaded {table:22s} {table_obj.num_rows:>8,} rows")

if __name__ == "__main__":
    main()

