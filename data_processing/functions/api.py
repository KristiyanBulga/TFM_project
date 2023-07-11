import boto3
import json
import logging

logging.getLogger().setLevel(logging.INFO)


def router(event, context):
    logging.info(f"Event: {event}")
    s3 = boto3.client('s3')
    # data = s3.get_object(Bucket="trip-advisor-dev", Key="weekly_query/g187486/2023/27/g187486_2023_07_09_07_00_00.json")
    # contents = data['Body'].read().decode("utf-8")
    # weekly_data = json.loads(contents)
    url = s3.generate_presigned_url(
        ClientMethod='get_object',
        Params={
            'Bucket': 'trip-advisor-dev',
            'Key': 'weekly_query/g187486/2023/27/g187486_2023_07_09_07_00_00.json'
        },
        ExpiresIn=3600  # one hour in seconds, increase if needed
    )
    return {
        "statusCode": 200,
        "body": json.dumps({"url": url})
        # "body": json.dumps(weekly_data)
    }
