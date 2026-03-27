"""
upload_to_s3.py — Upload all collected data to the S3 bucket.
Run this after running all collect_*.py scripts.

Usage:
  export S3_BUCKET_NAME=trialscope-de-documents
  python scripts/upload_to_s3.py
"""

import boto3
import json
import os
import mimetypes
from pathlib import Path
from datetime import datetime

BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "trialscope-de-documents")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR.parent / "data"

UPLOAD_MAP = [
    {"local_dir": DATA_DIR / "raw_trials", "s3_prefix": "raw-trials/", "source": "ClinicalTrials.gov", "file_types": [".json"]},
    {"local_dir": DATA_DIR / "fda_reviews", "s3_prefix": "fda-reviews/", "source": "FDA", "file_types": [".pdf", ".json"]},
    {"local_dir": DATA_DIR / "de_reports", "s3_prefix": "de-reports/", "source": "Delaware DPH", "file_types": [".pdf", ".json"]},
    {"local_dir": DATA_DIR / "pubmed", "s3_prefix": "pubmed/", "source": "PubMed", "file_types": [".json"]},
]

def main():
    print("TrialScope DE — Upload to S3")
    print(f"Bucket: {BUCKET_NAME} | Region: {AWS_REGION}\n")

    s3 = boto3.client("s3", region_name=AWS_REGION)

    # Create bucket if needed
    try:
        s3.head_bucket(Bucket=BUCKET_NAME)
    except:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=BUCKET_NAME)
        else:
            s3.create_bucket(Bucket=BUCKET_NAME, CreateBucketConfiguration={"LocationConstraint": AWS_REGION})

    for prefix in ["extracted/", "embeddings/"]:
        s3.put_object(Bucket=BUCKET_NAME, Key=prefix, Body=b"")

    total_uploaded = 0
    for config in UPLOAD_MAP:
        local_dir = config["local_dir"]
        if not local_dir.exists():
            print(f"Skipping {config['source']} (directory not found — run collection script first)")
            continue

        files = [f for f in local_dir.iterdir() if f.suffix in config["file_types"]]
        print(f"Uploading {len(files)} files from {config['source']}...")

        for filepath in sorted(files):
            s3_key = f"{config['s3_prefix']}{filepath.name}"
            content_type, _ = mimetypes.guess_type(str(filepath))
            metadata = {"source": config["source"], "upload-date": datetime.now().isoformat()}

            with open(filepath, "rb") as f:
                s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=f.read(),
                              ContentType=content_type or "application/octet-stream", Metadata=metadata)
            total_uploaded += 1

    print(f"\nDone! Uploaded {total_uploaded} files to s3://{BUCKET_NAME}/")
    print(f"Verify: aws s3 ls s3://{BUCKET_NAME}/ --recursive --human-readable")

if __name__ == "__main__":
    main()
