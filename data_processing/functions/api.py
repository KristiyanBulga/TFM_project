import logging

from functions.api_weekly_query import get_weekly_query
from functions.api_restaurant_data import get_restaurant_data
from functions.api_restaurant_reviews import get_restaurant_reviews

logging.getLogger().setLevel(logging.INFO)


def router(event, context):
    logging.info(f"Event: {event}")
    path = event.get('path', None)
    if path is None:
        return {
            "statusCode": 400,
            "headers": {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
            },
            "body": "No path parameter"
        }
    if path == '/data/combined':
        return get_weekly_query(event)
    elif path == '/data/trip_advisor':
        return get_restaurant_data(event, "trip_advisor")
    elif path == '/data/google_maps':
        return get_restaurant_data(event, "google_maps")
    elif path == '/reviews/trip_advisor':
        return get_restaurant_reviews(event, "trip_advisor")
    elif path == '/reviews/google_maps':
        return get_restaurant_reviews(event, "google_maps")
    else:
        return {
            "statusCode": 404,
            "headers": {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
            },
            "body": "Endpoint not found"
        }
