import json
import logging
from datetime import datetime
from utils.helper_wo_pandas import get_from_dynamo, notif_configs_db, update_item_dynamo, delete_item_dynamo, notifs_db

variable_text = {
    'ta_pos': '(Trip Advisor) Posición',
    'ta_num_reviews': '(Trip Advisor) Nº reviews semanal',
    'ta_mean_reviews': '(Trip Advisor) Media puntuaciones de las reviews semanal',
    'gm_num_reviews': '(Google Maps) Nº reviews semanal',
    'gm_mean_reviews': '(Google Maps) Media puntuaciones de las reviews semanal'
}
condition_transform = {'smaller': '<', 'equal': '=', 'bigger': '>'}
conditions = {'<': 'menor que', '=': 'igual que', '>': 'mayor que'}


def get_notification_configs(event):
    body = json.loads(event.get("body", "{}"))
    username = body.get("username", "NO USERNAME")
    key_cond_expr = "#username = :username"
    expr_names = {
        "#username": "username"
    }
    expr_attr = {
        ":username": {
            "S": username}
    }
    list_configs = get_from_dynamo(notif_configs_db, key_cond_expr, expr_names, expr_attr)
    res = []
    for config in list_configs:
        timestamp = config.get('timestamp', {}).get('N')
        restaurant_id = config.get('restaurant_id', {}).get('S')
        restaurant_name = config.get('restaurant_name', {}).get('S')
        variable = config.get('variable_name', {}).get('S')
        condition = config.get('condition_type', {}).get('S')
        value = config.get('value_comparisson', {}).get('N')
        print(restaurant_id, restaurant_name, variable, condition, value)
        if not (timestamp and restaurant_id and restaurant_name and variable and condition and value is not None):
            logging.error(f"There are not sufficient information to provide this config for user: {username}")
            continue

        filter_s = f"{variable_text[variable]} {conditions[condition]} {value}"

        data = {
            'timestamp': timestamp,
            'restaurant_id': restaurant_id,
            'restaurant': restaurant_name,
            'filter': filter_s
        }
        res.append(data)
    sorted_res = sorted(res, key=lambda x: x['timestamp'], reverse=True)
    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(sorted_res)
    }


def add_notification_config(event):
    body = json.loads(event.get("body", "{}"))
    username = body.get("username")
    restaurant_id = body.get("restaurant_id")
    restaurant_name = body.get("restaurant_name")
    variable = body.get("variable")
    condition = body.get("condition")
    value = body.get("value")
    if not (username and restaurant_id and restaurant_name and variable and condition and value is not None):
        return {
            "statusCode": 400,
            "headers": {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
            },
            "body": "Bad request body"
        }

    today = datetime.today()
    timestamp = int(today.timestamp() * 1000)
    key = {
        'username': {'S': username},
        'timestamp': {'N': str(timestamp)}
    }
    upd_expr = 'SET restaurant_name = :rest_name, restaurant_id = :rest_id, variable_name = :var, condition_type =:cond, value_comparisson = :val'
    expression_attr = {
        ':rest_name': {'S': restaurant_name},
        ':rest_id': {'S': restaurant_id},
        ':var': {'S': variable},
        ':cond': {'S': condition_transform[condition]},
        ':val': {'N': str(value)},
    }
    update_item_dynamo(notif_configs_db, key, upd_expr, expression_attr)
    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps({"text": "Notification configuration created correctly"})
    }


def delete_notification_config(event):
    body = json.loads(event.get("body", "{}"))
    username = body.get("username")
    timestamp = body.get("timestamp")
    if not (username and timestamp is not None):
        return {
            "statusCode": 400,
            "headers": {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True,
            },
            "body": "Bad request body"
        }

    key = {
        'username': {'S': username},
        'timestamp': {'N': str(timestamp)}
    }
    delete_item_dynamo(notif_configs_db, key)
    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps({"text": "Notification configuration deleted correctly"})
    }


def get_notifications(event):
    body = json.loads(event.get("body", "{}"))
    username = body.get("username")
    key_cond_expr = "#username = :username"
    expr_names = {
        "#username": "username"
    }
    expr_attr = {
        ":username": {
            "S": username}
    }
    list_notifs = get_from_dynamo(notifs_db, key_cond_expr, expr_names, expr_attr)
    res = []
    for config in list_notifs:
        timestamp = config.get('timestamp', {}).get('N')
        restaurant_id = config.get('restaurant_id', {}).get('S')
        restaurant_name = config.get('restaurant_name', {}).get('S')
        notif_message = config.get('notif_message', {}).get('S')
        print(restaurant_id, restaurant_name, notif_message)
        if not (timestamp and restaurant_id and restaurant_name and notif_message):
            logging.error(f"There are not sufficient information to provide this notif for user: {username}")
            continue
        data = {
            'timestamp': timestamp,
            'restaurant_id': restaurant_id,
            'restaurant': restaurant_name,
            'message': notif_message,
            'date': datetime.fromtimestamp(int(timestamp)/1000).strftime("%Y/%m/%d")
        }
        res.append(data)

    sorted_res = sorted(res, key=lambda x: x['timestamp'], reverse=True)
    print(sorted_res)
    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(sorted_res)
    }
