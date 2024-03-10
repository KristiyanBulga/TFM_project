import os
import json
import boto3
import logging
import requests
from datetime import datetime
from utils.helper import store_in_dynamo, update_dynamodb_item, basic_fields, contact_fields, atmosphere_fields, \
    store_in_s3_bucket, google_maps_bucket

logging.getLogger().setLevel(logging.INFO)
candidates_db = f'google-maps-candidates-db-{os.environ["stage"]}'
restaurants_db = f'restaurants-db-{os.environ["stage"]}'


def handler(event, context) -> None:
    """
    Given a trip advisor restaurant obtain the Google Maps data for that restaurant
    """
    for request in event.get("Records", []):
        body = json.loads(request.get("body", "{}"))
        logging.info(f"Event body: {body}")

        # File from where we are going to take restaurant name and address
        ta_place_id = body.get("ta_place_id")
        ta_restaurant_id = body.get("ta_restaurant_id")
        gm_restaurant_id = body.get("gm_restaurant_id")
        today = datetime.today()
        date_iso = today.isocalendar()

        # Prepare request for google maps API
        fields = basic_fields + contact_fields + atmosphere_fields
        google_maps_api_key = os.environ.get('GOOGLE_MAPS_API')

        url = "https://maps.googleapis.com/maps/api/place/details/json?"
        url += f"place_id={gm_restaurant_id}"
        url += f"&fields={'%2C'.join(fields)}"
        url += f"&language=es"
        url += f"&reviews_sort=newest"
        url += f"&key={google_maps_api_key}"

        payload = {}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)
        data = json.loads(response.content)

        # If query went wrong, notify the problem
        if data.get("status") != "OK":
            logging.error(f"Something went wrong, got status {data.get('status')}. Notifying through SNS")
            data["custom_message"] = "error, google maps, data obtain"
            sns = boto3.client('sns')
            sns.publish(
                TopicArn=os.environ.get('GOOGLE_MAPS_NOTIFY_ADMIN_TOPIC_ARN'),
                Message=json.dumps(data)
            )
            return

        filename = f"{gm_restaurant_id}_{today.strftime('%Y_%m_%d_%H_%M_%S')}"
        s3_path = f"raw_data/restaurants/{ta_place_id}/{ta_restaurant_id}/{today.year}/{today.month}/{today.day}"
        store_in_s3_bucket(google_maps_bucket, s3_path, data, filename)
        logging.info(f"[{ta_place_id}-{ta_restaurant_id}] Stored in S3 restaurant with id {gm_restaurant_id}")

        # STORE IN RESTAURANTS DB TABLE
        logging.info("Updating restaurants table")
        key = {
            'ta_place_id': {'S': ta_place_id},
            'ta_restaurant_id': {'S': ta_restaurant_id}
        }
        update_exp = 'SET google_maps_last_time = :new_date'
        att_values = {
            ':new_date': {'S': today.strftime("%Y/%m/%d, %H:%M:%S")}
        }
        update_dynamodb_item(restaurants_db, key, update_exp, att_values)
