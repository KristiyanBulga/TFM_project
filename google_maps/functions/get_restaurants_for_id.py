import os
import re
import json
import boto3
import logging
from datetime import datetime
from boto3.dynamodb.conditions import Key

logging.getLogger().setLevel(logging.INFO)


def handler(event, context) -> None:
    """
    For each trip advisor restaurant, add to queue to obtain Google Maps id
    """
    # get event data
    ta_place_id = event.get("trip_advisor_place_id", None)
    if ta_place_id is None:
        logging.error("missing trip_advisor_place_id variable in the event")
        return

    # obtain list of restaurants
    dynamodb = boto3.client('dynamodb')
    restaurants_db = f'restaurants-db-{os.environ["stage"]}'
    response = dynamodb.query(
        TableName=restaurants_db,
        IndexName='GoogleMapsIdFinder',
        KeyConditionExpression="ta_place_id = :place_id and google_maps_id = :not_searched",
        ExpressionAttributeValues={
            ":place_id": {
                "S": ta_place_id},
            ":not_searched": {
                "S": "not_searched"}
        }
    )
    list_restaurants = response.get('Items')

    logging.info(list_restaurants)

    # Add to queue
    today = datetime.today()
    today_iso = today.isocalendar()
    # add to queue restaurant
    for restaurant in list_restaurants:
        ta_restaurant_id = restaurant.get("ta_restaurant_id")
        trip_advisor_last_time = restaurant.get("trip_advisor_last_time")
        data = {
            "ta_place_id": ta_place_id,
            "ta_restaurant_id": ta_restaurant_id,
            "trip_advisor_last_time": trip_advisor_last_time,
            "week_triggered": f"{today_iso.year}-{today_iso.week}"
        }

        sqs_queue_name = f"google-maps-find-id-{os.environ['stage']}"
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=sqs_queue_name)
        queue.send_message(MessageBody=json.dumps(data))
        logging.info(f"Added to queue: {data['trip_advisor_complete_id']}")
        return
