import os
import re
import json
import boto3
import logging
from datetime import datetime

logging.getLogger().setLevel(logging.INFO)


def handler(event, context) -> None:
    """
    For each restaurant link, add to queue the obtainment of data for this restaurant
    event: day of the month
    context: month of the year
    Returns: None
    """
    # get event data
    ta_place_id = event.get("trip_advisor_place_id", None)
    if ta_place_id is None:
        logging.error("missing trip_advisor_place_id variable in the event")
        return

    # obtain list of restaurants
    if event.get("custom_date", None) is not None:
        today = datetime.strptime(event["custom_date"], "%Y_%m_%d_%H_%M_%S")
    else:
        today = datetime.today()
    today_iso = today.isocalendar()
    s3 = boto3.client('s3')
    bucket = 'trip-advisor-dev'
    result = s3.list_objects(Bucket=bucket, Prefix=f'raw_data/links/{ta_place_id}/{today_iso.year}/{today_iso.week}/')
    first_element = result.get('Contents')[0]
    data = s3.get_object(Bucket=bucket, Key=first_element.get('Key'))
    contents = data['Body'].read().decode("utf-8")
    links_dict = json.loads(contents)
    list_restaurants = links_dict.get("restaurants", [])

    # add to queue restaurant
    for restaurant in list_restaurants:
        ta_id = re.search('(?<=Restaurant_Review-)(.*)(?=-Reviews)', restaurant.get("link")).group(0)
        data = {
            "link": restaurant.get("link"),
            "trip_advisor_complete_id": ta_id,
            "restaurant_name": restaurant.get("name"),
            "week_obtained_link": f"{today_iso.year}-{today_iso.week}"
        }
        if event.get("custom_date", None) is not None:
            data["custom_date"] = event["custom_date"]

        sqs_queue_name = f"trip-advisor-queue-{os.environ['stage']}"
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=sqs_queue_name)
        queue.send_message(MessageBody=json.dumps(data))
        logging.info(f"Added to queue: {data['trip_advisor_complete_id']}")
