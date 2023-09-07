import boto3
import json
import logging
from datetime import datetime, timedelta


def get_weekly_query(event):
    s3 = boto3.client('s3')
    ta_place_id = "g187486"  # Take it from the event when having multiple places
    today = datetime.today()
    if today.weekday() != 6:
        today = today - timedelta(days=today.weekday() + 1)
    date_iso = today.isocalendar()
    prefix = f'weekly_query/{ta_place_id}/{date_iso.year}/{date_iso.week}/'
    result = s3.list_objects(Bucket="trip-advisor-dev", Prefix=prefix)
    if result.get('Contents') is None:
        return {
            "statusCode": 400,
            "headers": {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
            },
            "body": f"S3 path not found: {prefix}"
        }
    first_element = result.get('Contents')[0]
    logging.info(f"Obtaining data from {first_element.get('Key')}")
    data = s3.get_object(Bucket="trip-advisor-dev", Key=first_element.get('Key'))
    contents = data['Body'].read().decode("utf-8")
    weekly_data = json.loads(contents)
    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(weekly_data)
    }
