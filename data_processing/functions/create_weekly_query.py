import boto3
import logging
from boto3.dynamodb.conditions import Key
from datetime import datetime
from utils.helper_wo_pandas import weekly_data_db, store_in_s3_bucket_wo_pandas, region, buckets


def handler(event, context) -> None:
    """
    Create the weekly query and store it in S3
    """
    ta_place_id = event.get("trip_advisor_place_id", None)
    if not ta_place_id:
        raise Exception("Trip advisor place ID is not in event")
    if event.get("custom_date", None) is not None:
        today = datetime.strptime(event["custom_date"], "%Y_%m_%d_%H_%M_%S")
    else:
        today = datetime.today()
    today_iso = today.isocalendar()

    # Query from dynamoDB
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(weekly_data_db)
    response = table.query(
      KeyConditionExpression=Key('ta_place_id').eq(ta_place_id)
    )
    logging.info(response)

    # Store data in S3
    filename = f"{ta_place_id}_{today.strftime('%Y_%m_%d_%H_%M_%S')}"
    s3_path = f"weekly_query/{ta_place_id}/{today_iso.year}/{today_iso.week}"
    store_in_s3_bucket_wo_pandas(buckets["trip_advisor"], s3_path, response.get("Items", []), filename)
