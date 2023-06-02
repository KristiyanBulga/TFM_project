import boto3
import json
import logging
import os
from datetime import datetime
from utils.helper import get_from_dynamo_with_index

logging.getLogger().setLevel(logging.INFO)


def schedule_get_restaurant_for_id(ta_place_id):
    # obtain list of restaurants
    restaurants_db = f'restaurants-db-{os.environ["stage"]}'
    index_name = 'GoogleMapsIdFinder'
    key_cond_expr = "ta_place_id = :place_id and google_maps_id = :not_searched"
    expr_attr = {
        ":place_id": {
            "S": ta_place_id},
        ":not_searched": {
            "S": "not_searched"}
    }
    list_restaurants = get_from_dynamo_with_index(restaurants_db, index_name, key_cond_expr, expr_attr)

    logging.info(f"Found {len(list_restaurants)} restaurants")

    # Add to queue
    today = datetime.today()
    today_iso = today.isocalendar()
    # add to queue restaurant
    for restaurant in list_restaurants:
        ta_restaurant_id = restaurant.get("ta_restaurant_id", {}).get("S", None)
        trip_advisor_last_time = restaurant.get("trip_advisor_last_time", {}).get("S", None)
        data = {
            "ta_place_id": ta_place_id,
            "ta_restaurant_id": ta_restaurant_id,
            "trip_advisor_last_time": trip_advisor_last_time,
            "week_triggered": f"{today_iso.year}-{today_iso.week}"
        }

        sqs_queue_name = f"google-maps-find-id-queue-{os.environ['stage']}"
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=sqs_queue_name)
        queue.send_message(MessageBody=json.dumps(data))
        logging.info(f"Added to queue {sqs_queue_name}: {ta_place_id}-{ta_restaurant_id}")


def schedule_get_restaurant_for_data(ta_place_id):
    # obtain list of restaurants
    restaurants_db = f'restaurants-db-{os.environ["stage"]}'
    index_name = 'ValidRestaurants'
    key_cond_expr = "ta_place_id = :place_id and valid = :valid"
    expr_attr = {
        ":place_id": {
            "S": ta_place_id},
        ":valid": {
            "S": "yes"}
    }
    list_restaurants = get_from_dynamo_with_index(restaurants_db, index_name, key_cond_expr, expr_attr)

    logging.info(f"Found {len(list_restaurants)} restaurants")

    # Add to queue
    today = datetime.today()
    today_iso = today.isocalendar()
    # add to queue restaurant
    for restaurant in list_restaurants:
        ta_restaurant_id = restaurant.get("ta_restaurant_id", {}).get("S", None)
        google_maps_id = restaurant.get("google_maps_id", {}).get("S", None)
        data = {
            "ta_place_id": ta_place_id,
            "ta_restaurant_id": ta_restaurant_id,
            "gm_restaurant_id": google_maps_id,
            "week_triggered": f"{today_iso.year}-{today_iso.week}"
        }

        sqs_queue_name = f"google-maps-get-data-queue-{os.environ['stage']}"
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=sqs_queue_name)
        queue.send_message(MessageBody=json.dumps(data))
        logging.info(f"Added to queue {sqs_queue_name}: {ta_place_id}-{ta_restaurant_id}")


def handler(event, context) -> None:
    """
    For each trip advisor restaurant, add to queue to obtain Google Maps id
    """
    # get event data
    ta_place_id = event.get("trip_advisor_place_id", None)
    data_to_obtain = event.get("data_to_obtain", None)
    if ta_place_id is None or data_to_obtain is None:
        logging.error("Missing data in the event. Expected keys: trip_advisor_place_id and data_to_obtain")
        return

    if data_to_obtain == "restaurant_id":
        schedule_get_restaurant_for_id(ta_place_id)
    elif data_to_obtain == "restaurant_data":
        schedule_get_restaurant_for_data(ta_place_id)
    else:
        logging.error(f"Wrong data_to_obtain value. Expected restaurant_id or restaurant_data. Obtained {data_to_obtain}")
