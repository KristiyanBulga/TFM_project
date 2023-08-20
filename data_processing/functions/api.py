import boto3
import json
import logging
from datetime import datetime, timedelta

logging.getLogger().setLevel(logging.INFO)


def router(event, context):
    logging.info(f"Event: {event}")
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
    # url = s3.generate_presigned_url(
    #     ClientMethod='get_object',
    #     Params={
    #         'Bucket': 'trip-advisor-dev',
    #         'Key': 'weekly_query/g187486/2023/27/g187486_2023_07_09_07_00_00.json'
    #     },
    #     ExpiresIn=3600  # one hour in seconds, increase if needed
    # )
    return {
        "statusCode": 200,
        "headers": {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Credentials': True,
        },
        # "body": json.dumps({"url": url})
        "body": json.dumps(weekly_data)
    }
