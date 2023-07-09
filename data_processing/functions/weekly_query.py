import boto3
import json
import logging
import os
import time
from datetime import datetime

logging.getLogger().setLevel(logging.INFO)

athena_databases = {
    "trip_advisor": "trip_advisor_database",
    "google_maps": "google_maps_database"
}
client = boto3.client('athena')
queries_bucket = "s3://trip-advisor-dev/queries"
query_columns = {
    "trip_advisor": ["ta_restaurant_id", "name", "symbol", "score_overall", "travellers_choice", "serves_breakfast",
                     "serves_brunch", "serves_lunch", "serves_dinner", "tags"]
}


def handler(event, context) -> None:
    """
    Create the weekly query and store it in S3
    """
    ta_place_id = event.get("trip_advisor_place_id", None)
    if event.get("custom_date", None) is not None:
        today = datetime.strptime(event["custom_date"], "%Y_%m_%d_%H_%M_%S")
    else:
        today = datetime.today()
    today_iso = today.isocalendar()

    # Get processed data from trip advisor
    trip_advisor_columns = '"' + '", "'.join(query_columns["trip_advisor"]) + '"'
    query_trip_advisor = client.start_query_execution(
        QueryString=f"SELECT {trip_advisor_columns} FROM data where year = '{today_iso.year}' and week = '{today_iso.week}'",
        QueryExecutionContext={
            'Database': athena_databases.get('trip_advisor')
        },
        ResultConfiguration={'OutputLocation': f'{queries_bucket}/trip_advisor_{today.timestamp()}'}
    )
    # Get processed data from google maps
    # query_google_maps = client.start_query_execution(
    #     QueryString=f"SELECT * FROM data where year = '{today_iso.year}' and week = '{today_iso.week}'",
    #     QueryExecutionContext={
    #         'Database': athena_databases.get('google_maps')
    #     },
    #     ResultConfiguration={'OutputLocation': f'{queries_bucket}/google_maps_{today.timestamp()}'}
    # )

    # TODO: use get_query_execution to detect if the query has succeded
    # TODO: create query with maxResults and use next token

    time.sleep(5)

    results = client.get_query_results(QueryExecutionId=query_trip_advisor['QueryExecutionId'])

    weekly_data = dict()
    for row in results["ResultSet"]["Rows"][1:]:
        data = row["Data"]
        logging.info(data)
        restaurant_id = data[0]["VarCharValue"]
        restaurant_data = {
            "restaurant_name": data[1].get("VarCharValue", None),
            "ta_symbol": data[2].get("VarCharValue", None),
            "ta_score_overall": data[3].get("VarCharValue", None),
            "ta_travellers_choice": data[4].get("VarCharValue", None),
            "ta_serves_breakfast": data[5].get("VarCharValue", None),
            "ta_serves_brunch": data[6].get("VarCharValue", None),
            "ta_serves_lunch": data[7].get("VarCharValue", None),
            "ta_serves_dinner": data[8].get("VarCharValue", None),
            "ta_tags": data[9].get("VarCharValue", None),
        }
        weekly_data[restaurant_id] = restaurant_data

    filename = f"{ta_place_id}_{today.strftime('%Y_%m_%d_%H_%M_%S')}"
    s3_path = f"weekly_query/{ta_place_id}/{today_iso.year}/{today_iso.week}"
    _store_in_s3_bucket("trip-advisor-dev", s3_path, weekly_data, filename)


def _data_to_file(data, filename, extension):
    path = "/tmp/"
    filename_w_extension = filename
    if extension == "json":
        filename_w_extension += ".json"
        path += filename_w_extension
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
            f.close()
        return path, filename_w_extension
    return None, filename


def _store_in_s3_bucket(bucket, s3_path, data, filename, extension="json"):
    s3_client = boto3.client('s3', region_name='us-east-1')
    path_file, filename_w_extension = _data_to_file(data, filename, extension)
    if path_file is None:
        logging.error("File extension selected is not available. Aborting saving")
        return
    s3_client.upload_file(path_file, bucket, f"{s3_path}/{filename_w_extension}")
    os.remove(path_file)

