import boto3
import json
import os

region = "eu-west-1"
CHROMEDRIVER_PATH = "/opt/chromedriver"
CHROMIUM_PATH = "/opt/chrome/chrome"


def _data_to_file(data, filename, extension="json"):
    path = f"/tmp/{filename}."
    if extension == "json":
        path += "json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"restaurants": data}, f, ensure_ascii=False)
            f.close()
        return path
    return None


def store_in_s3_bucket(bucket, s3_path, data, filename):
    s3_client = boto3.client('s3', region_name=region)
    path_file = _data_to_file(data, filename)
    s3_client.upload_file(path_file, bucket, s3_path)
    os.remove(path_file)
