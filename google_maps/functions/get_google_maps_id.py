import os
import json
import boto3
import botocore
import logging
import requests
from datetime import datetime
from difflib import SequenceMatcher
from utils.helper import store_in_dynamo, update_dynamodb_item

logging.getLogger().setLevel(logging.INFO)
candidates_db = f'google-maps-candidates-db-{os.environ["stage"]}'
restaurants_db = f'restaurants-db-{os.environ["stage"]}'


def handler(event, context) -> None:
    """
    Given a trip advisor restaurant obtain the Google Maps id
    """
    for request in event.get("Records", []):
        body = json.loads(request.get("body", "{}"))
        logging.info(f"Event body: {body}")

        # File from where we are going to take restaurant name and address
        ta_place_id = body.get("ta_place_id")
        ta_restaurant_id = body.get("ta_restaurant_id")
        trip_advisor_last_time = body.get("trip_advisor_last_time")
        date = datetime.strptime(trip_advisor_last_time, '%Y/%m/%d, %H:%M:%S')
        date_iso = date.isocalendar()
        file_name = f"{ta_place_id}-{ta_restaurant_id}_{date.strftime('%Y_%m_%d_%H_%M_%S')}"
        s3_key = f"raw_data/restaurants/{ta_place_id}/{ta_restaurant_id}/{date_iso.year}/{date_iso.week}/{file_name}.json"

        # GET RESTAURANT NAME AND ADDRESS FROM S3 FILE
        logging.info(f"Getting S3 file with key: {s3_key}")
        s3_client = boto3.client('s3')
        bucket = 'trip-advisor-dev'
        ta_data = s3_client.get_object(
            Bucket=bucket,
            Key=s3_key
        )
        restaurant_data = json.loads(ta_data['Body'].read().decode("utf-8"))
        restaurant_name = restaurant_data.get('ta_restaurant').get('name')
        restaurant_address = restaurant_data.get('ta_restaurant').get('data').get('address')

        # Prepare request for google maps API
        fields = ["place_id", "name", "formatted_address"]
        google_maps_api_key = os.environ.get('GOOGLE_MAPS_API')

        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?"
        url += f"input={'%20'.join(restaurant_name.split())}"
        url += f"&inputtype=textquery"
        url += f"&fields={'%2C'.join(fields)}"
        url += f"&key={google_maps_api_key}"

        payload = {}
        headers = {}

        # Obtain data from google maps
        response = requests.request("GET", url, headers=headers, data=payload)
        data = json.loads(response.content)

        today = datetime.today()

        # If query went wrong store in database the problem
        if data.get("status") != "OK":
            try:
                item = {
                    'ta_place_id': {'S': ta_place_id},
                    'ta_restaurant_id': {'S': ta_restaurant_id},
                    'details': {'S': json.dumps(data)},
                    'method': {'S': data.get("status")},
                    'validated': {'N': '0'},
                    'date': {'S': today.strftime("%Y/%m/%d, %H:%M:%S")},
                    'ts': {'N': str(int(today.timestamp()))}
                }
                condition_exp = 'attribute_not_exists(ta_place_id) AND attribute_not_exists(ta_restaurant_id)'
                store_in_dynamo(candidates_db, item, condition_exp)
            except botocore.exceptions.ClientError as e:
                logging.info(f"[{ta_place_id}-{ta_restaurant_id}] exists in the candidates table")
            logging.info("Updating restaurants table")
            key = {
                'ta_place_id': {'S': ta_place_id},
                'ta_restaurant_id': {'S': ta_restaurant_id}
            }
            update_exp = 'SET valid = :valid, google_maps_id = :google_maps_id'
            att_values = {
                ':valid': {'S': "no"},
                ':google_maps_id': {'S': 'not_found'}
            }
            update_dynamodb_item(restaurants_db, key, update_exp, att_values)
            return
        # If multiples candidates select one
        selected = None
        if len(data.get("candidates")) > 1:
            logging.info("Multiple candidates found")
            if restaurant_address:
                candidates_distances = [
                    (SequenceMatcher(None, restaurant_address["name"], c["formatted_address"]).ratio(), c["place_id"])
                    for c in data.get("candidates")
                ]
                candidates_sorted = list(sorted(candidates_distances, key=lambda x: x[0], reverse=True))
                candidates_str = ", ".join([gm_id for _, gm_id in candidates_sorted])
                selected = candidates_sorted[0][1]
                method = "ADDRESS_SIMILARITY"
            else:
                candidates_str = ", ".join([c.get("place_id") for c in data.get("candidates")])
                selected = data.get("candidates")[0].get("place_id")
                method = "FIRST_CANDIDATE"
            # Store in dynamodb candidates table
            try:
                item = {
                    'ta_place_id': {'S': ta_place_id},
                    'ta_restaurant_id': {'S': ta_restaurant_id},
                    'sorted_candidates': {'S': candidates_str},
                    'selected': {'S': selected},
                    'details': {'S': json.dumps(data.get("candidates"))},
                    'method': {'S': method},
                    'validated': {'N': '0'},
                    'date': {'S': today.strftime("%Y/%m/%d, %H:%M:%S")},
                    'ts': {'N': str(int(today.timestamp()))}
                }
                condition_exp = 'attribute_not_exists(ta_place_id) AND attribute_not_exists(ta_restaurant_id)'
                logging.info("Storing in candidates dynamoDB table")
                store_in_dynamo(candidates_db, item, condition_exp)
            except botocore.exceptions.ClientError as e:
                logging.info(f"[{ta_place_id}-{ta_restaurant_id}] exists in the candidates table")
                return
            ## Send to SQS topic --> Notify administrator that a conflict was found
            sns = boto3.client('sns')
            logging.info("Notifying through SNS topic")
            item["custom_message"] = "error, google maps, id obtain"
            sns.publish(
                TopicArn=os.environ.get('GOOGLE_MAPS_NOTIFY_ADMIN_TOPIC_ARN'),
                Message=json.dumps(item)
            )

        else:
            selected = data.get("candidates")[0].get("place_id")

        # STORE IN RESTAURANTS DB TABLE
        logging.info("Updating restaurants table")
        key = {
            'ta_place_id': {'S': ta_place_id},
            'ta_restaurant_id': {'S': ta_restaurant_id}
        }
        update_exp = 'SET valid = :valid, google_maps_id = :google_maps_id'
        att_values = {
            ':valid': {'S': "yes"},
            ':google_maps_id': {'S': selected}
        }
        update_dynamodb_item(restaurants_db, key, update_exp, att_values)
