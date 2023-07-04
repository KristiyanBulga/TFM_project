import json
import boto3
import logging
import os
from datetime import datetime, date
from html import unescape
from utils.helper import buckets, get_from_dynamo_with_index, store_in_s3_bucket, update_item_dynamo, comments_db

logging.getLogger().setLevel(logging.INFO)
ta_day_conversion = {"lun": "lunes", "mar": "martes", "mié": "miércoles", "jue": "jueves", "vie": "viernes",
                     "sáb": "sábado", "dom": "domingo"}

def _data_process_trip_advisor(restaurant_data: dict, ta_place_id: str, ta_restaurant_id: str, today: datetime):
    logging.info(f"Restaurant {ta_place_id}-{ta_restaurant_id}: processing data from Trip Advisor")
    restaurant_k = restaurant_data["ta_restaurant"]
    data = restaurant_k["data"]
    prices = data["price"] if data.get("price") is not None else {}
    restaurant_info = {
        "ta_restaurant_id": ta_restaurant_id,
        "added_ts": int(today.timestamp() * 100),
        "name": unescape(restaurant_k.get("name", "")),
        "url": restaurant_k.get("link", ""),
        "symbol": json.dumps([s.count('€') for s in data["symbol"].split("-")] if data.get("symbol") is not None else []),
        "claimed": data.get("claimed", False),
        "price_lower": prices.get("lower"),
        "price_upper": prices.get("upper"),
        "score_overall": data.get("score_overall"),
        "score_food": data.get("score_food"),
        "score_service": data.get("score_service"),
        "score_price_quality": data.get("score_price_quality"),
        "score_atmosphere": data.get("score_atmosphere"),
        "ranking": data.get("ranking"),
        "travellers_choice": data.get("travellers_choice", False),
        "address": data.get("address", {}).get("name"),
        "webpage": data.get("webpage"),
        "phone": data.get("phone"),
        "serves_breakfast": "Desayuno" in data["meals"] if data.get("meals") is not None else False,
        "serves_brunch": "Brunch" in data["meals"] if data.get("meals") is not None else False,
        "serves_lunch": "Comidas" in data["meals"] if data.get("meals") is not None else False,
        "serves_dinner": "Cenas" in data["meals"] if data.get("meals") is not None else False
    }
    if restaurant_info["price_lower"] is not None and restaurant_info["price_lower"] is not None:
        restaurant_info["price_mean"] = restaurant_info["price_upper"] - restaurant_info["price_lower"]
    elif restaurant_info["price_lower"] is not None:
        restaurant_info["price_mean"] = restaurant_info["price_lower"]
    elif restaurant_info["price_upper"] is not None:
        restaurant_info["price_mean"] = restaurant_info["price_upper"]
    else:
        restaurant_info["price_mean"] = None
    schedule = dict()
    days = data["schedule"] if data.get("schedule") else {}
    for day in days.keys():
        schedule[ta_day_conversion[day]] = data["schedule"][day]
    restaurant_info["schedule"] = json.dumps(schedule)
    tags = dict()
    tags["type"] = data["type"] if data.get("type") is not None else []
    tags["special_diets"] = data["special_diets"] if data.get("special_diets") is not None else []
    tags["meals"] = data["meals"] if data.get("meals") is not None else []
    tags["advantages"] = data["advantages"] if data.get("advantages") is not None else []
    restaurant_info["tags"] = json.dumps(tags)

    # Store in a file the reviews
    reviews = data.get("reviews", [])
    logging.info(f"Found {len(reviews)} reviews for {ta_place_id}-{ta_restaurant_id}")
    for review in reviews:
        date_review = datetime.strptime(review["date_review"], '%Y_%m_%d').date()
        datetime_review = datetime.combine(date_review, datetime.now().time())
        key = {
            'place': {'S': f"{ta_place_id}-{ta_restaurant_id}"},
            'timestamp': {'N': str(int(datetime_review.timestamp() * 1000))}
        }
        upd_expr = 'SET rate = :rvw_rate, title = :rvw_title, review = :rvw_text, platform =:rvw_platform'
        expression_attr = {
            ':rvw_rate': {'N': str(review["rating"])},
            ':rvw_title': {'S': review["title"]},
            ':rvw_text': {'S': review["text"]},
            ':rvw_platform': {'S': "trip_advisor"}
        }
        update_item_dynamo(comments_db, key, upd_expr, expression_attr)
    return restaurant_info


def _data_process_google_maps(restaurant_data: dict, ta_place_id: str, ta_restaurant_id: str, today: datetime):
    logging.info(f"Restaurant {ta_place_id}-{ta_restaurant_id}: processing data from Google Chrome")
    data = restaurant_data["result"]
    restaurant_info = {
        "ta_restaurant_id": ta_restaurant_id,
        "gm_place_id": data.get("place_id"),
        "added_ts": int(today.timestamp() * 100),
        "name": data["name"],
        "url": data.get("url", ""),
        "symbol": data.get("price_level"),
        "score_overall": data.get("rating"),
        "address": data.get("formatted_address"),
        "webpage": data.get("website"),
        "phone": data.get("international_phone_number"),
        "business_status": data.get("business_status", "OPERATIONAL"),
        "serves_lunch": data.get("serves_lunch", False),
        "serves_dinner": data.get("serves_dinner", False),
        "serves_beer": data.get("serves_beer", False),
        "serves_vegetarian_food": data.get("serves_vegetarian_food", False),
        "serves_wine": data.get("serves_wine", False),
        "takeout": data.get("takeout", False),
        "wheelchair_accessible_entrance": data.get("wheelchair_accessible_entrance", False),
        "dine_in": data.get("dine_in", False),
        "delivery": data.get("delivery", False),
        "reservable": data.get("delivery", False),
    }

    schedule = dict()
    for working_day in data.get("opening_hours", {}).get("weekday_text", []):
        day, info = working_day.split(':', 1)
        list_hours = []
        for hour_info in info.split('–'):
            hour_list = hour_info.split(' ')
            if len(hour_list) == 2 and hour_list[1] == "PM":
                hour, mi = hour_list[0].split(':')
                hour = int(hour) + 12
                list_hours.append(f"{hour}:{mi}")
            else:
                list_hours.append(hour_list[0].strip())
        schedule[day] = list_hours
    restaurant_info["schedule"] = json.dumps(schedule)

    # Store in a file the reviews
    reviews = data.get("reviews", [])
    logging.info(f"Found {len(reviews)} reviews for {ta_place_id}-{ta_restaurant_id}")
    for review in reviews:
        timestamp = review["time"]
        key = {
            'place': {'S': f"{ta_place_id}-{ta_restaurant_id}"},
            'timestamp': {'N': str(int(timestamp * 1000))}
        }
        upd_expr = 'SET rate = :rvw_rate, review = :rvw_text, platform =:rvw_platform'
        expression_attr = {
            ':rvw_rate': {'N': str(review["rating"])},
            ':rvw_text': {'S': review["text"]},
            ':rvw_platform': {'S': "trip_advisor"}
        }
        update_item_dynamo(comments_db, key, upd_expr, expression_attr)
    return restaurant_info


def handler(event, context) -> None:
    """
    Given a place and a platform, process all the obtained data
    """

    ta_place_id = event.get("trip_advisor_place_id", None)
    platform = event.get("platform", None)
    if ta_place_id is None or platform is None:
        logging.error(f"Missing data in the event. Expected keys: trip_advisor_place_id and platform. Event: {event}")
        return
    if event.get("custom_date", None) is not None:
        today = datetime.strptime(event["custom_date"], "%Y_%m_%d_%H_%M_%S")
    else:
        today = datetime.today()
    today_iso = today.isocalendar()

    # Get all the valid restaurants
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

    bucket = buckets.get(platform, None)
    if bucket is None:
        logging.error(f"The platform does not exist or does not have : {event}")
        return

    # For each restaurant obtain the info and process it
    restaurants_data = []
    for restaurant in list_restaurants:
        ta_restaurant_id = restaurant.get("ta_restaurant_id", {}).get("S", None)
        s3 = boto3.client('s3')
        logging.info(f"path: raw_data/restaurants/{ta_place_id}/{ta_restaurant_id}/{today_iso.year}/{today_iso.week}/")
        result = s3.list_objects(Bucket=bucket, Prefix=f'raw_data/restaurants/{ta_place_id}/{ta_restaurant_id}/{today_iso.year}/{today_iso.week}/')
        if result.get('Contents') is not None:
            first_element = result.get('Contents')[0]
            data = s3.get_object(Bucket=bucket, Key=first_element.get('Key'))
            contents = data['Body'].read().decode("utf-8")
            restaurant_data = json.loads(contents)
            if platform == "trip_advisor":
                restaurants_data.append(_data_process_trip_advisor(restaurant_data, ta_place_id, ta_restaurant_id, today))
            elif platform == "google_maps":
                restaurants_data.append(_data_process_google_maps(restaurant_data, ta_place_id, ta_restaurant_id, today))

    filename = f"{platform}_{today.strftime('%Y_%m_%d_%H_%M_%S')}"
    s3_path = f"restaurants/data/ta_place_id={ta_place_id}/year={today_iso.year}/week={today_iso.week}"
    store_in_s3_bucket(bucket, s3_path, restaurants_data, filename, extension="parquet")
