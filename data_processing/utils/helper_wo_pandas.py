import boto3
import json
import logging
import os
from decimal import Decimal

dynamodb = boto3.client('dynamodb')
logging.getLogger().setLevel(logging.INFO)
region = os.environ['region']
stage = os.environ['stage']
buckets = {
    "trip_advisor": f'trip-advisor-{stage}',
    "google_maps": f'google-maps-bucket-{stage}'
}
comments_db = f"comments-db-{stage}"
weekly_data_db = f"list-restaurants-data-db-{stage}"


def get_from_dynamo_with_index(table_name: str, index_name: str, key_cond_expr: str, expr_attr: dict) -> list:
    """
    This function makes a query to the dynamoDB using the params
    :param table_name: name of the dynamoDB table
    :param index_name: name of the index
    :param key_cond_expr: the condition
    :param expr_attr: values for the condition expression
    :return: the list of items from dynamoDB
    """
    response = dynamodb.query(
        TableName=table_name,
        IndexName=index_name,
        KeyConditionExpression=key_cond_expr,
        ExpressionAttributeValues=expr_attr
    )
    return response.get('Items')


def update_item_dynamo(table, key, update_expr, expression_attr):
    dynamodb.update_item(
        TableName=table,
        Key=key,
        UpdateExpression=update_expr,
        ExpressionAttributeValues=expression_attr
    )


def _data_to_file(data, filename, extension):
    path = "/tmp/"
    filename_w_extension = filename
    if extension == "json":
        filename_w_extension += ".json"
        path += filename_w_extension
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, cls=JSONEncoder)
            f.close()
        return path, filename_w_extension
    return None, filename


def store_in_s3_bucket_wo_pandas(bucket, s3_path, data, filename, extension="json"):
    s3_client = boto3.client('s3', region_name=region)
    path_file, filename_w_extension = _data_to_file(data, filename, extension)
    if path_file is None:
        logging.error("File extension selected is not available. Aborting saving")
        return
    s3_client.upload_file(path_file, bucket, f"{s3_path}/{filename_w_extension}")
    os.remove(path_file)


def parse_athena_boolean(value: str) -> bool:
    return value == "true"


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)
