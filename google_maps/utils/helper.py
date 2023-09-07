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


def store_in_dynamo(table_name: str, item: dict, condition_exp: str = None) -> None:
    """
    This function inserts an item into a dynamoDB table if a condition is fulfilled
    :param table_name: name of the dynamoDB table
    :param item: the dynamo item we want to insert
    :param condition_exp: the condition that must be fulfilled before putting the item
    """
    try:
        dynamodb.put_item(
            TableName=table_name,
            Item=item,
            ConditionExpression=condition_exp
        )
    except botocore.exceptions.ClientError as e:
        logging.info(f"An error has happen while trying to store in dynamo table: {table_name}. Item: {item}. Condition: {condition_exp}. Error: {e}")


def update_dynamodb_item(table_name: str, key: dict, update_exp: str, att_values: dict) -> None:
    """
    This function updates an item in the dynamoDB table using the params
    :param table_name: name of the dynamoDB table
    :param key: key of the item
    :param update_exp: the update expression where the columns to be modified are specified
    :param att_values: values for the condition expression
    """
    dynamodb.update_item(TableName=table_name, Key=key, UpdateExpression=update_exp,
                         ExpressionAttributeValues=att_values)
    logging.info(f"Updated correctly item from table {table_name}. Key: {key}. Expression: {update_exp}. Attributes: {att_values}")


def _data_to_file(data: dict, filename: str, extension: str):
    """
    Generates a file with the specified extension
    :param data: the data that is going to be stored
    :param filename: the name of the file
    :param extension: the type of file it is generated
    returns: the path of the generated file and the name of the file with the file type extension

    """
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


def store_in_s3_bucket(bucket: str, s3_path: str, data: dict, filename: str, extension: str = "json"):
    """
    Stores the data into given the bucket name and the key
    :param bucket: name of the bucket
    :param s3_path: path/key where the data is going to be stored
    :param data: data to be stored
    :param filename: name of the file where the data will be stored
    :param extension: the type of file
    """
    s3_client = boto3.client('s3', region_name=region)
    path_file, filename_w_extension = _data_to_file(data, filename, extension)
    if path_file is None:
        logging.error("File extension selected is not available. Aborting saving")
        return
    s3_client.upload_file(path_file, bucket, f"{s3_path}/{filename_w_extension}")
    os.remove(path_file)
