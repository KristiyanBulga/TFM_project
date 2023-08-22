import boto3
import json
import logging
from datetime import datetime, timedelta

logging.getLogger().setLevel(logging.INFO)


def get_restaurant_reviews(event, platform):
    body = json.loads(event.get("body", "{}"))
    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": "No ni na"
    }
