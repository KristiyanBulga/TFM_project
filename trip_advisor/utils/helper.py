import boto3
import logging
import json
import os

region = "eu-west-1"
CHROMEDRIVER_PATH = "/opt/chromedriver"
CHROMIUM_PATH = "/opt/headless-chromium"


def _data_to_file(data, filename, extension="json"):
    path = "/tmp/"
    filename_w_extension = filename
    if extension == "json":
        filename_w_extension += ".json"
        path += filename_w_extension
        with open(path, 'w', encoding='utf-8') as f:
            json.dump({"restaurants": data}, f, ensure_ascii=False)
            f.close()
        return path, filename_w_extension
    return None, filename


def store_in_s3_bucket(bucket, s3_path, data, filename):
    s3_client = boto3.client('s3', region_name=region)
    path_file, filename_w_extension = _data_to_file(data, filename)
    if path_file is None:
        logging.error("File extension selected is not available. Aborting saving")
        return
    s3_client.upload_file(path_file, bucket, f"{s3_path}/{filename_w_extension}")
    os.remove(path_file)
