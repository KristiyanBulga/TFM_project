import boto3
import json
import logging

logging.getLogger().setLevel(logging.INFO)


def router(event, context):
    logging.info(f"Event: {event}")
    s3 = boto3.client('s3')
    data = s3.get_object(Bucket="trip-advisor-dev", Key="weekly_query/g187486/2023/26/g187486_2023_07_02_01_00_00.json")
    contents = data['Body'].read().decode("utf-8")
    weekly_data = json.loads(contents)
    return {
        "statusCode": 200,
        "body": json.dumps(weekly_data)
    }
