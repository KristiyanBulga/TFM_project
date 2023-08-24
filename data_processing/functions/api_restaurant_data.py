import boto3
import json
import logging
import time
from datetime import datetime
from utils.helper_wo_pandas import parse_athena_boolean


logging.getLogger().setLevel(logging.INFO)

athena_databases = {
    "trip_advisor": "trip_advisor_database",
    "google_maps": "google_maps_database"
}
query_columns = {
    "trip_advisor": ["symbol", "price_lower", "price_upper", "score_overall", "score_food", "score_service",
                     "score_price_quality", "score_atmosphere", "ranking", "year", "week"],
    "google_maps": ["symbol", "score_overall", "year", "week"]
}
client = boto3.client('athena')
queries_bucket = "s3://trip-advisor-dev/queries"


def trip_advisor_parser(data):
    res = {
        "restaurant_id": data[0].get("VarCharValue", "-"),
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
        "week": int(data[27]["VarCharValue"]) if data[27].get("VarCharValue") is not None else '-',
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
        "name": data[3].get("VarCharValue", "-"),
        "url": data[4].get("VarCharValue", "-"),
        "symbol": int(float(data[5]["VarCharValue"])) if data[5].get("VarCharValue") is not None else '-',
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
        "place_id": data[22].get("VarCharValue", "-"),
        "year": int(data[23]["VarCharValue"]) if data[23].get("VarCharValue") is not None else '-',
        "week": int(data[24]["VarCharValue"]) if data[24].get("VarCharValue") is not None else '-',
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
    for row in rows:
        data = row["Data"]
        symbols = json.loads(data[0].get("VarCharValue", "[]"))
        historical["symbol"].append(sum(symbols)/len(symbols) if symbols else None)
        historical["price_lower"].append(float(data[1].get("VarCharValue")) if data[1].get("VarCharValue") else None)
        historical["price_upper"].append(float(data[2].get("VarCharValue")) if data[2].get("VarCharValue") else None)
        historical["score_overall"].append(float(data[3].get("VarCharValue")) if data[3].get("VarCharValue") else None)
        historical["score_food"].append(float(data[4].get("VarCharValue")) if data[4].get("VarCharValue") else None)
        historical["score_service"].append(float(data[5].get("VarCharValue")) if data[5].get("VarCharValue") else None)
        historical["score_price_quality"].append(float(data[6].get("VarCharValue")) if data[6].get("VarCharValue") else None)
        historical["score_atmosphere"].append(float(data[7].get("VarCharValue")) if data[7].get("VarCharValue") else None)
        historical["ranking"].append(int(float(data[8].get("VarCharValue"))) if data[8].get("VarCharValue") else None)
        historical["year"].append(int(data[9].get("VarCharValue")) if data[9].get("VarCharValue") else None)
        historical["week"].append(int(data[10].get("VarCharValue")) if data[10].get("VarCharValue") else None)
    return historical


def google_maps_historical(rows):
    historical = {x: [] for x in query_columns["google_maps"]}
    print("ROWS", rows)
    for row in rows:
        data = row["Data"]
        symbols = int(float(data[0]["VarCharValue"])) if data[0].get("VarCharValue") else None
        historical["symbol"].append(symbols if symbols else -1)
        historical["score_overall"].append(float(data[1].get("VarCharValue")) if data[1].get("VarCharValue") else None)
        historical["year"].append(int(data[2].get("VarCharValue")) if data[2].get("VarCharValue") else None)
        historical["week"].append(int(data[3].get("VarCharValue")) if data[3].get("VarCharValue") else None)
    return historical


def get_restaurant_data(event, platform):
    body = json.loads(event.get("body", "{}"))
    # Get processed data from athena
    query_trip_advisor = client.start_query_execution(
        QueryString=f"SELECT * FROM data where ta_place_id = '{body.get('place_id')}' and ta_restaurant_id = '{body.get('restaurant_id')}' order by year, week DESC limit 1",
        QueryExecutionContext={
            'Database': athena_databases.get(platform)
        },
        ResultConfiguration={'OutputLocation': f'{queries_bucket}/{platform}_data_{datetime.today().timestamp()}'}
    )

    query_execution = client.get_query_execution(QueryExecutionId=query_trip_advisor['QueryExecutionId'])
    query_state = query_execution["QueryExecution"]["Status"]["State"]
    seconds = 60
    while query_state in ["QUEUED", "RUNNING"] and seconds > 0:
        time.sleep(1)
        query_execution = client.get_query_execution(QueryExecutionId=query_trip_advisor['QueryExecutionId'])
        query_state = query_execution["QueryExecution"]["Status"]["State"]
        seconds -= 1

    if query_state != "SUCCEEDED":
        logging.error(f"Athena query was aborted in status {query_state}. Query execution: {query_execution}")
        return

    results = client.get_query_results(QueryExecutionId=query_trip_advisor['QueryExecutionId'])
    res = dict()
    for row in results["ResultSet"]["Rows"][1:]:
        data = row["Data"]
        if platform == 'trip_advisor':
            res = trip_advisor_parser(data)
        if platform == 'google_maps':
            res = google_maps_parser(data)

    # HISTORICAL DATA

    query_columns_str = '"' + '", "'.join(query_columns[platform]) + '"'
    query_trip_advisor = client.start_query_execution(
        QueryString=f"SELECT {query_columns_str} FROM data where ta_place_id = '{body.get('place_id')}' and ta_restaurant_id = '{body.get('restaurant_id')}' order by year, week ASC",
        QueryExecutionContext={
            'Database': athena_databases.get(platform)
        },
        ResultConfiguration={'OutputLocation': f'{queries_bucket}/{platform}_history_{datetime.today().timestamp()}'}
    )

    query_execution = client.get_query_execution(QueryExecutionId=query_trip_advisor['QueryExecutionId'])
    logging.info(f'QUERY {query_execution}')
    query_state = query_execution["QueryExecution"]["Status"]["State"]
    seconds = 60
    while query_state in ["QUEUED", "RUNNING"] and seconds > 0:
        time.sleep(1)
        query_execution = client.get_query_execution(QueryExecutionId=query_trip_advisor['QueryExecutionId'])
        query_state = query_execution["QueryExecution"]["Status"]["State"]
        seconds -= 1

    if query_state != "SUCCEEDED":
        logging.error(f"Athena query was aborted in status {query_state}. Query execution: {query_execution}")
        return

    results = client.get_query_results(QueryExecutionId=query_trip_advisor['QueryExecutionId'])
    logging.info(f'RESULT {results}')
    if platform == 'trip_advisor':
        res["historical"] = trip_advisor_historical(results["ResultSet"]["Rows"][1:])
    if platform == 'google_maps':
        res["historical"] = google_maps_historical(results["ResultSet"]["Rows"][1:])

    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(res)
    }
