import json
import time
import boto3
import logging
from datetime import datetime, timedelta
from utils.helper_wo_pandas import get_from_dynamo, notif_configs_db, update_item_dynamo, notifs_db, candidates_db, \
    reviews_history_db, update_item_dynamo

client = boto3.client('athena')
queries_bucket = "s3://trip-advisor-dev/queries"
variable_text = {
    'ta_pos': '(Trip Advisor) Posición',
    'ta_num_reviews': '(Trip Advisor) Nº reviews semanal',
    'ta_mean_reviews': '(Trip Advisor) Media puntuaciones de las reviews semanal',
    'gm_num_reviews': '(Google Maps) Nº reviews semanal',
    'gm_mean_reviews': '(Google Maps) Media puntuaciones de las reviews semanal'
}
conditions = {'<': 'menor que', '=': 'igual que', '>': 'mayor que'}


def get_restaurant_data(restaurant_id):
    # Get processed data from athena
    query_trip_advisor = client.start_query_execution(
        QueryString=f"SELECT * FROM data where ta_place_id = 'g187486' and ta_restaurant_id = '{restaurant_id}' order by year, week DESC limit 1",
        QueryExecutionContext={
            'Database': 'trip_advisor_database'
        },
        ResultConfiguration={'OutputLocation': f'{queries_bucket}/notifications_data_{datetime.today().timestamp()}'}
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
    return results["ResultSet"]["Rows"][1]["Data"]


def get_reviews_history(platform, restaurant_id, year, week):
    primary_key = f'g187486-{restaurant_id}'
    key_cond_expr = "#place = :place_id and #details = :details"
    detail = f"{year}-{week}-{platform}"
    expr_names = {
        "#place": "place",
        "#details": "detail"
    }
    expr_attr = {
        ":place_id": {
            "S": primary_key},
        ":details": {
            "S": detail},
    }
    list_reviews = get_from_dynamo(reviews_history_db, key_cond_expr, expr_names, expr_attr)
    review = list_reviews[0]
    return {
        "count": int(review.get('num_reviews', {}).get('N', '-1')),
        "mean": float(review.get('mean_reviews', {}).get('N', '-1'))
    }


def condition_fulfilled(var_value, condition, value):
    if condition == '<':
        return var_value < value
    elif condition == '=':
        return var_value == value
    elif condition == '>':
        return var_value > value
    return False


def update_dynamo(username, restaurant_name, restaurant_id, msg, times = None):
    if times is None:
        timestamp = int(datetime.today().timestamp() * 1000)
    else:
        timestamp = times * 1000
    key = {
        'username': {'S': username},
        'timestamp': {'N': str(timestamp)}
    }
    upd_expr = 'SET restaurant_name = :rest_name, restaurant_id = :rest_id, notif_message = :msg'
    expression_attr = {
        ':rest_name': {'S': restaurant_name},
        ':rest_id': {'S': restaurant_id},
        ':msg': {'S': msg}
    }
    update_item_dynamo(notifs_db, key, upd_expr, expression_attr)


def handler(event, context) -> None:
    """
    Stores the new notifications
    """

    username = "propietario@gmail.com"  # Modify when having multiple users
    key_cond_expr = "#username = :username"
    expr_names = {
        "#username": "username"
    }
    expr_attr = {
        ":username": {
            "S": username}
    }
    list_configs = get_from_dynamo(notif_configs_db, key_cond_expr, expr_names, expr_attr)

    ta_data = {}
    reviews_history = {}

    for config in list_configs:
        timestamp = config.get('timestamp', {}).get('N')
        restaurant_id = config.get('restaurant_id', {}).get('S')
        restaurant_name = config.get('restaurant_name', {}).get('S')
        variable = config.get('variable_name', {}).get('S')
        condition = config.get('condition_type', {}).get('S')
        value = config.get('value_comparisson', {}).get('N')
        print(restaurant_id, restaurant_name, variable, condition, value)
        if not (timestamp and restaurant_id and restaurant_name and variable and condition and value is not None):
            logging.error(f"There are not sufficient information to use this config for user: {username}")
            continue
        print(config)

        msg = ""
        if restaurant_id not in reviews_history.keys():
            today = datetime.today()
            if today.weekday() == 6 and today.hour < 8:
                today = today - timedelta(weeks=1)
            today_iso = today.isocalendar()

            ta_reviews = get_reviews_history("trip_advisor", restaurant_id, today_iso.year, today_iso.week)
            gm_reviews = get_reviews_history("google_maps", restaurant_id, today_iso.year, today_iso.week)
            reviews_history[restaurant_id] = {
                'trip_advisor': ta_reviews,
                'google_maps': gm_reviews
            }

        if variable == 'ta_pos':
            if restaurant_id not in ta_data.keys():
                ta_data[restaurant_id] = get_restaurant_data(restaurant_id)
            data = ta_data[restaurant_id]
            ranking = int(float(data[13]["VarCharValue"])) if data[13].get("VarCharValue") is not None else 99999
            if condition_fulfilled(ranking, condition, int(value)):
                msg = f"{variable_text[variable]} {conditions[condition]} {value}"
        elif variable == 'ta_num_reviews':
            var_value = reviews_history[restaurant_id]['trip_advisor']["count"]
            if condition_fulfilled(var_value, condition, int(value)):
                msg = f"{variable_text[variable]} {conditions[condition]} {value}"
        elif variable == 'ta_mean_reviews':
            var_value = reviews_history[restaurant_id]['trip_advisor']["mean"]
            if condition_fulfilled(var_value, condition, int(value)):
                msg = f"{variable_text[variable]} {conditions[condition]} {value}"
        elif variable == 'gm_num_reviews':
            var_value = reviews_history[restaurant_id]['google_maps']["count"]
            if condition_fulfilled(var_value, condition, int(value)):
                msg = f"{variable_text[variable]} {conditions[condition]} {value}"
        elif variable == 'gm_mean_reviews':
            var_value = reviews_history[restaurant_id]['google_maps']["mean"]
            if condition_fulfilled(var_value, condition, int(value)):
                msg = f"{variable_text[variable]} {conditions[condition]} {value}"
        if msg != "":
            update_dynamo(username, restaurant_name, restaurant_id, msg)

# # # # # # ADMIN PART


def handler_admin(event, context):
    username = "admin@gmail.com"  # Modify when having multiple users
    key_cond_expr = "#place = :place"
    expr_names = {
        "#place": "ta_place_id"
    }
    expr_attr = {
        ":place": {
            "S": 'g187486'}
    }
    list_candidates = get_from_dynamo(candidates_db, key_cond_expr, expr_names, expr_attr)
    for row in list_candidates:
        notified = row.get("notified", {}).get('S', None)
        if notified is None or notified == 'no':
            ta_place_id = row['ta_place_id']['S']
            ta_restaurant_id = row['ta_restaurant_id']['S']
            restaurant = f"{ta_place_id}-{ta_restaurant_id}"
            msg = ""
            print(row.get("method", {}).get('S'), row.get("method", {}).get('S', 'ZERO_RESULTS') == 'ZERO_RESULTS')
            if row.get("method", {}).get('S', 'ZERO_RESULTS') == 'ZERO_RESULTS':
                msg = f"No se han encontrado candidatos para este restaurante"
            elif row.get("sorted_candidates", {}).get('S', None) is not None:
                msg = f"Se ha seleccionado el candidato {row['selected']['S']} de la lista de candidatos: [{row['sorted_candidates']['S']}]"
            if msg != "":
                update_dynamo(username, restaurant, row['ta_restaurant_id']['S'], msg, times=int(row['ts']['N']))
                key = {
                    'ta_place_id': {'S': ta_place_id},
                    'ta_restaurant_id': {'S': ta_restaurant_id}
                }
                update_exp = 'SET notified = :notified'
                att_values = {
                    ':notified': {'S': "yes"}
                }
                update_item_dynamo(candidates_db, key, update_exp, att_values)
