import boto3
import botocore
import json
import logging
import os

region = "us-east-1"
dynamodb = boto3.client('dynamodb')
google_maps_bucket = f"google-maps-bucket-{os.environ['stage']}"
basic_fields = ["address_components", "adr_address", "business_status", "formatted_address", "geometry", "icon", "name",
                "place_id", "photo", "place_id", "plus_code", "type", "url", "utc_offset", "vicinity",
                "wheelchair_accessible_entrance"]
contact_fields = ["current_opening_hours", "formatted_phone_number", "international_phone_number", "opening_hours",
                  "secondary_opening_hours", "website"]
atmosphere_fields = ["curbside_pickup", "delivery", "dine_in", "editorial_summary", "price_level", "rating",
                     "reservable", "reviews", "serves_beer", "serves_breakfast", "serves_brunch", "serves_dinner",
                     "serves_lunch", "serves_vegetarian_food", "serves_wine", "takeout", "user_ratings_total"]


def get_from_dynamo_with_index(table_name, index_name, key_cond_expr, expr_attr):
    response = dynamodb.query(
        TableName=table_name,
        IndexName=index_name,
        KeyConditionExpression=key_cond_expr,
        ExpressionAttributeValues=expr_attr
    )
    return response.get('Items')


def store_in_dynamo(table_name: str, item: dict, condition_exp:str=None) -> None:
    try:
        dynamodb.put_item(
            TableName=table_name,
            Item=item,
            ConditionExpression=condition_exp
        )
    except botocore.exceptions.ClientError as e:
        logging.info(f"An error has happen while trying to store in dynamo table: {table_name}. Item: {item}. Condition: {condition_exp}. Error: {e}")


def update_dynamodb_item(table_name: str, key: dict, update_exp: str, att_values: dict) -> None:
    dynamodb.update_item(TableName=table_name, Key=key, UpdateExpression=update_exp,
                         ExpressionAttributeValues=att_values)
    logging.info(f"Updated correctly item from table {table_name}. Key: {key}. Expression: {update_exp}. Attributes: {att_values}")


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
    return None, filename


def store_in_s3_bucket(bucket, s3_path, data, filename, extension="json"):
    s3_client = boto3.client('s3', region_name=region)
    path_file, filename_w_extension = _data_to_file(data, filename, extension)
    if path_file is None:
        logging.error("File extension selected is not available. Aborting saving")
        return
    s3_client.upload_file(path_file, bucket, f"{s3_path}/{filename_w_extension}")
    os.remove(path_file)
