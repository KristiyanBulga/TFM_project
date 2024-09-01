import json
import time
import boto3
import logging
from boto3.dynamodb.conditions import Key
from datetime import datetime
from utils.helper_wo_pandas import parse_athena_boolean, weekly_data_db, store_in_s3_bucket_wo_pandas, region, buckets


def handler(event, context) -> None:
    """
    Create the daily query and store it in S3
    """
    ta_place_id = event.get("trip_advisor_place_id", None)
    if not ta_place_id:
        raise Exception("Trip advisor place ID is not in event")
    if event.get("custom_date", None) is not None:
        today = datetime.strptime(event["custom_date"], "%Y_%m_%d_%H_%M_%S")
    else:
        today = datetime.today()

    # Query from dynamoDB
    dynamodb = boto3.resource('dynamodb', region_name=region)
    table = dynamodb.Table(weekly_data_db)
    response = table.query(
        KeyConditionExpression=Key('ta_place_id').eq(ta_place_id)
    )
    items = response.get("Items", [])
    if ta_place_id == "g187486":
        response2 = table.query(
            KeyConditionExpression=Key('ta_place_id').eq("g1435704")
        )
        items.extend(response2.get("Items", []))
    logging.info(response)

    daily_data = []
    restaurant_tuples = []
    for restaurant in items:
        restaurant_tuples.append((restaurant["ta_place_id"], restaurant["ta_restaurant_id"]))
        if restaurant.get("gm_added", None) is None or restaurant.get("restaurant_name", None) is None:
            continue
        data = {
            "place_id": restaurant["ta_place_id"],
            "restaurant_id": restaurant["ta_restaurant_id"],
            "restaurant_name": restaurant["restaurant_name"],
            "dates": {
                "trip_advisor": restaurant["ta_added"],
                "google_maps": restaurant["gm_added"]
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
        if restaurant.get("ta_serves_breakfast", False):
            data["services"].append("serves breakfast")
        if restaurant.get("ta_serves_brunch", False):
            data["services"].append("serves brunch")
        data["location"] = json.loads(restaurant.get("place_location", "{}"))

        data["photo"] = restaurant.get("photo")

        daily_data.append(data)

    # Store data in S3
    filename = f"{ta_place_id}_{today.strftime('%Y_%m_%d_%H_%M_%S')}"
    s3_path = f"daily_query/{ta_place_id}/{today.year}/{today.month}/{today.day}"
    store_in_s3_bucket_wo_pandas(buckets["processed_data"], s3_path, daily_data, filename)

    for option in restaurant_tuples:
        get_restaurant_data({"place_id": option[0], "restaurant_id": option[1]}, "trip_advisor")
        get_restaurant_data({"place_id": option[0], "restaurant_id": option[1]}, "google_maps")

### Athena queries

athena_databases = {
    "trip_advisor": "trip_advisor_database",
    "google_maps": "google_maps_database"
}
athena_tables = {
    "trip_advisor": "platform_trip_advisor",
    "google_maps": "platform_google_maps",
}
query_columns = {
    "trip_advisor": ["symbol", "price_lower", "price_upper", "score_overall", "score_food", "score_service",
                     "score_price_quality", "score_atmosphere", "ranking", "year", "month", "day"],
    "google_maps": ["symbol", "score_overall", "year", "month", "day"]
}
client = boto3.client('athena')
queries_bucket = "s3://data-process-bucket-dev/queries"

def trip_advisor_parser(data):
    res = {
        "restaurant_id": data[0].get("VarCharValue", "-"),
        "added": data[1].get("VarCharValue", "-"),
        "name": data[2].get("VarCharValue", "-"),
        "url": data[3].get("VarCharValue", "-"),
        "claimed": parse_athena_boolean(data[5].get("VarCharValue", "-")),
        "price_lower": float(data[6]["VarCharValue"]) if data[6].get("VarCharValue") is not None else '-',
        "price_upper": float(data[7]["VarCharValue"]) if data[7].get("VarCharValue") is not None else '-',
        "score_overall": float(data[8]["VarCharValue"]) if data[8].get("VarCharValue") is not None else '-',
        "score_food": float(data[9]["VarCharValue"]) if data[9].get("VarCharValue") is not None else '-',
        "score_service": float(data[10]["VarCharValue"]) if data[10].get("VarCharValue") is not None else '-',
        "score_price_quality": float(data[11]["VarCharValue"]) if data[11].get("VarCharValue") is not None else '-',
        "score_atmosphere": float(data[12]["VarCharValue"]) if data[12].get("VarCharValue") is not None else '-',
        "ranking": int(float(data[13]["VarCharValue"])) if data[13].get("VarCharValue") is not None else '-',
        "travellers_choice": parse_athena_boolean(data[14].get("VarCharValue", "-")),
        "address": data[15].get("VarCharValue", "-"),
        "webpage": data[16].get("VarCharValue", "-"),
        "phone": data[17].get("VarCharValue", "-"),
        "serves_breakfast": parse_athena_boolean(data[18].get("VarCharValue", "-")),
        "serves_brunch": parse_athena_boolean(data[19].get("VarCharValue", "-")),
        "serves_lunch": parse_athena_boolean(data[20].get("VarCharValue", "-")),
        "serves_dinner": parse_athena_boolean(data[21].get("VarCharValue", "-")),
        "price_mean": float(data[22]["VarCharValue"]) if data[22].get("VarCharValue") is not None else '-',
        "place_id": data[25].get("VarCharValue", "-"),
        "year": int(data[26]["VarCharValue"]) if data[26].get("VarCharValue") is not None else '-',
        "month": int(data[27]["VarCharValue"]) if data[27].get("VarCharValue") is not None else '-',
        "day": int(data[28]["VarCharValue"]) if data[28].get("VarCharValue") is not None else '-',
    }
    symbols = json.loads(data[4].get("VarCharValue", "[]"))
    res["symbol"] = "-".join(['€' * x for x in symbols]) if symbols else '-'
    schedule = json.loads(data[23].get("VarCharValue", '{}'))
    schedule_processed = dict()
    for key in schedule.keys():
        hours = schedule[key]
        grouped_hours = []
        for i in range(0, len(hours), 2):
            if i + 1 < len(hours):
                grouped_hours.append("-".join([hours[i], hours[i + 1]]))
            else:
                grouped_hours.append(hours[i])
        schedule_processed[key] = ", ".join(grouped_hours)
    res["schedule"] = schedule_processed
    tags = json.loads(data[24].get("VarCharValue", '{}'))
    tags_processed = []
    for key in tags.keys():
        tags_processed += tags[key]
    res["tags"] = tags_processed
    return res


def google_maps_parser(data):
    res = {
        "restaurant_id": data[0].get("VarCharValue", "-"),
        "added": data[2].get("VarCharValue", "-"),
        "name": data[3].get("VarCharValue", "-"),
        "url": data[4].get("VarCharValue", "-"),
        "symbol": '€' * int(float(data[5]["VarCharValue"])) if data[5].get("VarCharValue") is not None else '-',
        "score_overall": float(data[6]["VarCharValue"]) if data[6].get("VarCharValue") is not None else '-',
        "address": data[7].get("VarCharValue", "-"),
        "webpage": data[8].get("VarCharValue", "-"),
        "phone": data[9].get("VarCharValue", "-"),
        "business_status": data[10].get("VarCharValue", "-"),
        "serves_lunch": parse_athena_boolean(data[11].get("VarCharValue", "-")),
        "serves_dinner": parse_athena_boolean(data[12].get("VarCharValue", "-")),
        "serves_beer": parse_athena_boolean(data[13].get("VarCharValue", "-")),
        "serves_vegetarian_food": parse_athena_boolean(data[14].get("VarCharValue", "-")),
        "serves_wine": parse_athena_boolean(data[15].get("VarCharValue", "-")),
        "takeout": parse_athena_boolean(data[16].get("VarCharValue", "-")),
        "wheelchair_accessible_entrance": parse_athena_boolean(data[17].get("VarCharValue", "-")),
        "dine_in": parse_athena_boolean(data[18].get("VarCharValue", "-")),
        "deliver": parse_athena_boolean(data[19].get("VarCharValue", "-")),
        "reservable": parse_athena_boolean(data[20].get("VarCharValue", "-")),
        "location": data[23].get("VarCharValue", "{}"),
        "place_id": data[24].get("VarCharValue", "-"),
        "year": int(data[25]["VarCharValue"]) if data[25].get("VarCharValue") is not None else '-',
        "week": int(data[26]["VarCharValue"]) if data[26].get("VarCharValue") is not None else '-',
    }
    schedule = json.loads(data[21].get("VarCharValue", '{}'))
    schedule_processed = dict()
    for key in schedule.keys():
        hours = schedule[key]
        schedule_processed[key] = "-".join(hours)
    res["schedule"] = schedule_processed
    return res


def trip_advisor_historical(rows):
    historical = {x: [] for x in query_columns["trip_advisor"]}
    historical['date'] = []
    for row in rows:
        data = row["Data"]
        year = int(data[9].get("VarCharValue")) if data[9].get("VarCharValue") else 1971
        month = int(data[10].get("VarCharValue")) if data[10].get("VarCharValue") else 1
        day = int(data[11].get("VarCharValue")) if data[11].get("VarCharValue") else 1
        date = datetime(year, month, day).strftime('%Y/%m/%d')
        symbols = json.loads(data[0].get("VarCharValue", "[]"))
        historical["symbol"].append(sum(symbols)/len(symbols) if symbols else None)
        historical["price_lower"].append({"x": date, "y": float(data[1].get("VarCharValue")) if data[1].get("VarCharValue") else None})
        historical["price_upper"].append({"x": date, "y": float(data[2].get("VarCharValue")) if data[2].get("VarCharValue") else None})
        historical["score_overall"].append({"x": date, "y": float(data[3].get("VarCharValue")) if data[3].get("VarCharValue") else None})
        historical["score_food"].append({"x": date, "y": float(data[4].get("VarCharValue")) if data[4].get("VarCharValue") else None})
        historical["score_service"].append({"x": date, "y": float(data[5].get("VarCharValue")) if data[5].get("VarCharValue") else None})
        historical["score_price_quality"].append({"x": date, "y": float(data[6].get("VarCharValue")) if data[6].get("VarCharValue") else None})
        historical["score_atmosphere"].append({"x": date, "y": float(data[7].get("VarCharValue")) if data[7].get("VarCharValue") else None})
        historical["ranking"].append({"x": date, "y": int(float(data[8].get("VarCharValue"))) if data[8].get("VarCharValue") else None})
        historical["date"].append(datetime(year, month, day).strftime('%Y/%m/%d'))
    return historical


def google_maps_historical(rows):
    historical = {x: [] for x in query_columns["google_maps"]}
    historical['date'] = []
    for row in rows:
        data = row["Data"]
        year = int(data[2].get("VarCharValue")) if data[2].get("VarCharValue") else 1971
        month = int(data[3].get("VarCharValue")) if data[3].get("VarCharValue") else 1
        day = int(data[4].get("VarCharValue")) if data[4].get("VarCharValue") else 1
        date = datetime(year, month, day).strftime('%Y/%m/%d')
        symbols = int(float(data[0]["VarCharValue"])) if data[0].get("VarCharValue") else None
        historical["symbol"].append(symbols if symbols else -1)
        historical["score_overall"].append({"x": date, "y": float(data[1].get("VarCharValue")) if data[1].get("VarCharValue") else None})
        historical["date"].append(date)
    return historical


def get_restaurant_data(body, platform):
    # Get processed data from athena
    query_columns_str = '"' + '", "'.join(query_columns[platform]) + '"'
    query_history = client.start_query_execution(
        QueryString=f"SELECT {query_columns_str} FROM {athena_tables.get(platform)} where ta_place_id = '{body.get('place_id')}' and ta_restaurant_id = '{body.get('restaurant_id')}' order by added_ts ASC",
        QueryExecutionContext={
            'Database': athena_databases.get(platform)
        },
        ResultConfiguration={'OutputLocation': f'{queries_bucket}/{platform}_history_{datetime.today().timestamp()}'}
    )

    query_last = client.start_query_execution(
        QueryString=f"SELECT * FROM ( SELECT  *, ROW_NUMBER() OVER ( PARTITION BY ta_restaurant_id ORDER BY added_ts DESC ) AS row_num FROM {athena_tables.get(platform)} ) AS aux_table WHERE aux_table.row_num = 1 and ta_place_id = '{body.get('place_id')}' and ta_restaurant_id = '{body.get('restaurant_id')}';",
        QueryExecutionContext={
            'Database': athena_databases.get(platform)
        },
        ResultConfiguration={'OutputLocation': f'{queries_bucket}/{platform}_data_{datetime.today().timestamp()}'}
    )

    query_execution = client.get_query_execution(QueryExecutionId=query_last['QueryExecutionId'])
    query_state = query_execution["QueryExecution"]["Status"]["State"]
    seconds = 60
    while query_state in ["QUEUED", "RUNNING"] and seconds > 0:
        time.sleep(1)
        query_execution = client.get_query_execution(QueryExecutionId=query_last['QueryExecutionId'])
        query_state = query_execution["QueryExecution"]["Status"]["State"]
        seconds -= 1

    if query_state != "SUCCEEDED":
        logging.error(f"Athena query was aborted in status {query_state}. Query execution: {query_execution}")
        return

    results = client.get_query_results(QueryExecutionId=query_last['QueryExecutionId'])
    res = dict()
    for row in results["ResultSet"]["Rows"][1:]:
        data = row["Data"]
        if platform == 'trip_advisor':
            res = trip_advisor_parser(data)
        if platform == 'google_maps':
            res = google_maps_parser(data)

    # HISTORICAL DATA

    query_execution = client.get_query_execution(QueryExecutionId=query_history['QueryExecutionId'])
    logging.info(f'QUERY {query_execution}')
    query_state = query_execution["QueryExecution"]["Status"]["State"]
    seconds = 60
    while query_state in ["QUEUED", "RUNNING"] and seconds > 0:
        time.sleep(1)
        query_execution = client.get_query_execution(QueryExecutionId=query_history['QueryExecutionId'])
        query_state = query_execution["QueryExecution"]["Status"]["State"]
        seconds -= 1

    if query_state != "SUCCEEDED":
        logging.error(f"Athena query was aborted in status {query_state}. Query execution: {query_execution}")
        return

    results = client.get_query_results(QueryExecutionId=query_history['QueryExecutionId'])
    logging.info(f'RESULT {results}')
    if platform == 'trip_advisor':
        res["historical"] = trip_advisor_historical(results["ResultSet"]["Rows"][1:])
    if platform == 'google_maps':
        res["historical"] = google_maps_historical(results["ResultSet"]["Rows"][1:])

    filename = f"{body.get('place_id')}_{body.get('restaurant_id')}_{platform}"
    s3_path = f"restaurant_queries"
    store_in_s3_bucket_wo_pandas(buckets["processed_data"], s3_path, res, filename)
