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

    weekly_data = []
    for restaurant in response.get("Items", []):
        if restaurant.get("gm_date", None) is None or restaurant.get("restaurant_name", None) is None:
            continue
        data = {
            "place_id": restaurant["ta_place_id"],
            "restaurant_id": restaurant["ta_restaurant_id"],
            "restaurant_name": restaurant["restaurant_name"],
            "dates": {
                "trip_advisor": restaurant["ta_date"],
                "google_maps": restaurant["gm_date"]
            },
            "scores": dict(),
            "symbol": dict(),
            "services": list(),
            "travellers_choice": restaurant["ta_travellers_choice"]
        }
        trip_advisor_score = float(restaurant["ta_score_overall"])
        google_maps_score = float(restaurant["gm_score_overall"])
        all_scores = [x for x in [trip_advisor_score, google_maps_score] if x >= 0]
        mean_score = round(sum(all_scores)/len(all_scores) if all_scores else -1, 2)
        data["scores"] = {
            "trip_advisor": trip_advisor_score,
            "google_maps": google_maps_score,
            "average": mean_score,
        }
        trip_advisor_symbol = float(restaurant["ta_symbol"])
        google_maps_symbol = float(restaurant["gm_symbol"])
        all_symbols = [x for x in [trip_advisor_symbol, google_maps_symbol] if x >= 0]
        mean_symbol = round(sum(all_symbols) / len(all_symbols) if all_symbols else -1)
        data["symbol"] = {
            "trip_advisor": trip_advisor_symbol,
            "google_maps": google_maps_symbol,
            "average": mean_symbol,
        }
        if restaurant.get("gm_deliver", False):
            data["services"].append("deliver")
        if restaurant.get("gm_dine_in", False):
            data["services"].append("dine in")
        if restaurant.get("gm_reservable", False):
            data["services"].append("reservable")
        if restaurant.get("gm_serves_beer", False):
            data["services"].append("serves beer")
        if restaurant.get("gm_serves_dinner", False) or restaurant.get("ta_serves_dinner", False):
            data["services"].append("serves dinner")
        if restaurant.get("gm_serves_lunch", False) or restaurant.get("ta_serves_lunch", False):
            data["services"].append("serves lunch")
        if restaurant.get("gm_serves_vegetarian_food", False):
            data["services"].append("serves vegetarian food")
        if restaurant.get("gm_serves_wine", False):
            data["services"].append("serves wine")
        if restaurant.get("gm_takeout", False):
            data["services"].append("takeout")
        if restaurant.get("gm_wheelchair_accessible_entrance", False):
            data["services"].append("wheelchair accessible entrance")
        if restaurant.get("ta_serves_brakfast", False):
            data["services"].append("serves brakfast")
        if restaurant.get("ta_serves_brunch", False):
            data["services"].append("serves brunch")

        weekly_data.append(data)

    # Store data in S3
    filename = f"{ta_place_id}_{today.strftime('%Y_%m_%d_%H_%M_%S')}"
    s3_path = f"weekly_query/{ta_place_id}/{today_iso.year}/{today_iso.week}"
    store_in_s3_bucket_wo_pandas(buckets["trip_advisor"], s3_path, weekly_data, filename)
