"""Stage a model in S3, then publish it only after the F1 quality gate."""

import argparse
import json
from pathlib import Path
import sys

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.quality_gate import check_quality

ARTIFACT_FILES = {
    "model.joblib": "models/model.joblib",
    "report.json": "outputs/report.json",
    "detail.txt": "outputs/detail.txt",
}


def validate_prefix(prefix):
    if not prefix.startswith("artifacts/runs/") or not prefix.removeprefix("artifacts/runs/"):
        raise ValueError("Candidate prefix must be artifacts/runs/<run-id>-<attempt>")
    if any(part in {"", ".", ".."} for part in prefix.split("/")):
        raise ValueError("Candidate prefix contains invalid path components")
    return prefix


def upload_candidate(bucket, prefix):
    validate_prefix(prefix)
    # Validate every input before making any cloud changes.
    for filename in ARTIFACT_FILES.values():
        if not Path(filename).is_file():
            raise FileNotFoundError(filename)
    client = boto3.client("s3")
    for name, filename in ARTIFACT_FILES.items():
        client.upload_file(filename, bucket, f"{prefix}/{name}")
    print(f"Uploaded candidate to s3://{bucket}/{prefix}")


def publish_candidate(bucket, prefix):
    validate_prefix(prefix)
    client = boto3.client("s3")
    # Recheck the staged report before touching the serving model.
    response = client.get_object(Bucket=bucket, Key=f"{prefix}/report.json")
    with response["Body"] as body:
        check_quality(json.load(body)["f1_score"])
    # Ensure the entire candidate exists before the first copy.
    for name in ARTIFACT_FILES:
        client.head_object(Bucket=bucket, Key=f"{prefix}/{name}")
    for name in ARTIFACT_FILES:
        client.copy_object(
            Bucket=bucket, Key=f"artifacts/current/{name}",
            CopySource={"Bucket": bucket, "Key": f"{prefix}/{name}"},
        )
    print("Published approved model to artifacts/current/")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["upload", "publish"])
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--prefix", required=True)
    args = parser.parse_args()
    try:
        operation = upload_candidate if args.operation == "upload" else publish_candidate
        operation(args.bucket, args.prefix)
    except (BotoCoreError, ClientError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"S3 artifact operation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
