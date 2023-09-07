import boto3
import json
import logging
import time
from datetime import datetime
from utils.helper_wo_pandas import store_in_s3_bucket_wo_pandas, parse_athena_boolean, update_item_dynamo, \
    weekly_data_db

logging.getLogger().setLevel(logging.INFO)

athena_databases = {
    "trip_advisor": "trip_advisor_database",
    "google_maps": "google_maps_database"
}
client = boto3.client('athena')
queries_bucket = "s3://trip-advisor-dev/queries"
query_columns = {
    "trip_advisor": ["ta_restaurant_id", "name", "symbol", "score_overall", "travellers_choice", "serves_breakfast",
                     "serves_brunch", "serves_lunch", "serves_dinner", "tags"],
    "google_maps": ["ta_restaurant_id", "symbol", "score_overall", "serves_lunch", "serves_dinner", "serves_beer",
                    "serves_vegetarian_food", "serves_wine", "takeout", "wheelchair_accessible_entrance", "dine_in",
                    "delivery", "reservable"]
}


def _get_new_weekly_data(today: datetime, platform: str, ta_place_id: str):
    today_iso = today.isocalendar()

    # Get processed data from athena
    query_columns_str = '"' + '", "'.join(query_columns[platform]) + '"'
    query_trip_advisor = client.start_query_execution(
        QueryString=f"SELECT {query_columns_str} FROM data where year = '{today_iso.year}' and week = '{today_iso.week}'",
        QueryExecutionContext={
            'Database': athena_databases.get(platform)
        },
        ResultConfiguration={'OutputLocation': f'{queries_bucket}/{platform}_{today.timestamp()}'}
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
    logging.info(f'Updating {len(results["ResultSet"]["Rows"][1:])} restaurants')
    for row in results["ResultSet"]["Rows"][1:]:
        data = row["Data"]
        logging.info(data)
        restaurant_id = data[0]["VarCharValue"]
        expression_attr = dict()
        upd_expr = ""
        if platform == "trip_advisor":
            symbol_list = json.loads(data[2].get("VarCharValue", "[]"))
            symbols = sum(symbol_list)/len(symbol_list) if symbol_list else -1
            expression_attr = {
                ":restaurant_name": {'S': data[1].get("VarCharValue", "")},
                ":ta_symbol": {'N': str(symbols)},
                ":ta_score_overall": {'N': data[3].get("VarCharValue", "-1")},
                ":ta_travellers_choice": {'BOOL': parse_athena_boolean(data[4].get("VarCharValue", "false"))},
                ":ta_serves_breakfast": {'BOOL': parse_athena_boolean(data[5].get("VarCharValue", "false"))},
                ":ta_serves_brunch": {'BOOL': parse_athena_boolean(data[6].get("VarCharValue", "false"))},
                ":ta_serves_lunch": {'BOOL': parse_athena_boolean(data[7].get("VarCharValue", "false"))},
                ":ta_serves_dinner": {'BOOL': parse_athena_boolean(data[8].get("VarCharValue", "false"))},
                ":ta_tags": {'S': data[9].get("VarCharValue", "{}")},
                ":ta_date": {'S': today.strftime("%Y/%m/%d, %H:%M:%S")}
            }
            upd_expr = 'SET restaurant_name = :restaurant_name, ta_symbol = :ta_symbol, ' + \
                       'ta_score_overall = :ta_score_overall, ta_travellers_choice = :ta_travellers_choice, ' + \
                       'ta_serves_breakfast = :ta_serves_breakfast, ta_serves_brunch = :ta_serves_brunch, ' + \
                       'ta_serves_lunch = :ta_serves_lunch, ta_serves_dinner = :ta_serves_dinner, ' + \
                       'ta_tags = :ta_tags, ta_date = :ta_date'
        elif platform == "google_maps":
            expression_attr = {
                ":gm_symbol": {'N': data[1].get("VarCharValue", "-1")},
                ":gm_score_overall": {'N': data[2].get("VarCharValue", "-1")},
                ":gm_serves_lunch": {'BOOL': parse_athena_boolean(data[3].get("VarCharValue", "false"))},
                ":gm_serves_dinner": {'BOOL': parse_athena_boolean(data[4].get("VarCharValue", "false"))},
                ":gm_serves_beer": {'BOOL': parse_athena_boolean(data[5].get("VarCharValue", "false"))},
                ":gm_serves_vegetarian_food": {'BOOL': parse_athena_boolean(data[6].get("VarCharValue", "false"))},
                ":gm_serves_wine": {'BOOL': parse_athena_boolean(data[7].get("VarCharValue", "false"))},
                ":gm_takeout": {'BOOL': parse_athena_boolean(data[8].get("VarCharValue", "false"))},
                ":gm_wheelchair_accessible_entrance": {'BOOL': parse_athena_boolean(data[9].get("VarCharValue", "false"))},
                ":gm_dine_in": {'BOOL': parse_athena_boolean(data[10].get("VarCharValue", "false"))},
                ":gm_deliver": {'BOOL': parse_athena_boolean(data[11].get("VarCharValue", "false"))},
                ":gm_reservable": {'BOOL': parse_athena_boolean(data[12].get("VarCharValue", "false"))},
                ":gm_date": {'S': today.strftime("%Y/%m/%d, %H:%M:%S")}
            }
            upd_expr = 'SET gm_symbol = :gm_symbol, gm_score_overall = :gm_score_overall, ' + \
                       'gm_serves_lunch = :gm_serves_lunch, gm_serves_dinner = :gm_serves_dinner, ' + \
                       'gm_serves_beer = :gm_serves_beer, gm_serves_vegetarian_food = :gm_serves_vegetarian_food, ' + \
                       'gm_serves_wine = :gm_serves_wine, gm_takeout = :gm_takeout, ' + \
                       'gm_wheelchair_accessible_entrance = :gm_wheelchair_accessible_entrance, ' + \
                       'gm_dine_in = :gm_dine_in, gm_deliver = :gm_deliver, gm_reservable = :gm_reservable, ' \
                       'gm_date = :gm_date'

        key = {
            'ta_place_id': {'S': ta_place_id},
            'ta_restaurant_id': {'S': restaurant_id}
        }
        update_item_dynamo(weekly_data_db, key, upd_expr, expression_attr)


def handler(event, context) -> None:
    """
    Update weekly data in dynamoDB
    """
    ta_place_id = event.get("trip_advisor_place_id", None)
    if not ta_place_id:
        raise Exception("Trip advisor place ID is not in event")
    if event.get("custom_date", None) is not None:
        today = datetime.strptime(event["custom_date"], "%Y_%m_%d_%H_%M_%S")
    else:
        today = datetime.today()

    _get_new_weekly_data(today, "trip_advisor", ta_place_id)
    _get_new_weekly_data(today, "google_maps", ta_place_id)
