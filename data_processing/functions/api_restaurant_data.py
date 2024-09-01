import boto3
import json
import logging


logging.getLogger().setLevel(logging.INFO)


def get_restaurant_data(event, platform):
    s3 = boto3.client('s3')
    body = json.loads(event.get("body", "{}"))
    data = s3.get_object(Bucket="data-process-bucket-dev", Key=f"restaurant_queries/{body.get('place_id')}_{body.get('restaurant_id')}_{platform}.json")
    contents = data['Body'].read().decode("utf-8")
    obj_data = json.loads(contents)
    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(obj_data)
    }
