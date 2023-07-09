import boto3
import json
import logging
import os
import pandas as pd
from utils.helper_wo_pandas import *

region = os.environ['region']


def _data_to_file(data, filename, extension):
    path = "/tmp/"
    filename_w_extension = filename
    if extension == "json":
        filename_w_extension += ".json"
        path += filename_w_extension
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            f.close()
        return path, filename_w_extension
    elif extension == "parquet":
        filename_w_extension += ".parquet"
        path += filename_w_extension
        df = pd.DataFrame(data)
        df.to_parquet(path, engine='pyarrow', use_dictionary=False)
        return path, filename_w_extension
    return None, filename


def store_in_s3_bucket(bucket, s3_path, data, filename, extension="json"):
    s3_client = boto3.client('s3', region_name=region)
    path_file, filename_w_extension = _data_to_file(data, filename, extension)
    if path_file is None:
        logging.error("File extension selected is not available. Aborting saving")
        return
    s3_client.upload_file(path_file, bucket, f"{s3_path}/{filename_w_extension}")
    os.remove(path_file)
