import boto3
import json
import logging
from datetime import datetime, timedelta
from utils.helper_wo_pandas import get_from_dynamo, comments_db, reviews_history_db, get_from_dynamo_with_index_with_limit, reviews_statistics_db

logging.getLogger().setLevel(logging.INFO)


def get_restaurant_reviews(event, amount: str = None):
    body = json.loads(event.get("body", "{}"))
    primary_key = f'{body.get("place_id")}-{body.get("restaurant_id")}'
    if amount == "last":
        key_cond_expr = "#place = :place_id"
        expr_names = {
            "#place": "place",
        }
        expr_attr = {
            ":place_id": {
                "S": primary_key},
        }
        print("DEBUG", primary_key)
        list_reviews = get_from_dynamo_with_index_with_limit(comments_db, "PlaceByTs", key_cond_expr, expr_names, expr_attr, 5)
    else:
        key_cond_expr = "#place = :place_id"
        expr_names = {
            "#place": "place"
        }
        expr_attr = {
            ":place_id": {
                "S": primary_key},
        }
        list_reviews = get_from_dynamo(comments_db, key_cond_expr, expr_names, expr_attr)
    _reviews = list()
    for review in list_reviews:
        timestamp = int(review.get('ts', {}).get('N', '0'))
        review_data = {
            "rate": float(review.get('rate', {}).get('N', '-1')),
            "review": review.get('review', {}).get('S', '-'),
            "platform": review.get('platform', {}).get('S', '-'),
            "timestamp": timestamp,
            "date": (datetime.fromtimestamp(timestamp/1000) + timedelta(hours=2)).strftime('%Y/%m/%d, %H:%M:%S')
        }
        if review["platform"].get('S') == "trip_advisor":
            review_data["title"] = review.get('title', {}).get('S')
        _reviews.append(review_data)

    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(_reviews)
    }

def get_restaurant_reviews_between_dates(event):
    body = json.loads(event.get("body", "{}"))
    primary_key = f'{body.get("place_id")}-{body.get("restaurant_id")}'
    date_start, date_end = body.get("date_start"), body.get("date_end")
    date_start, date_end = [int(x) for x in date_start.split("/")],[int(x) for x in date_end.split("/")]
    ts_start = datetime(date_start[0], date_start[1], date_start[2]).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    ts_end = datetime(date_end[0], date_end[1], date_end[2]).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    print(ts_start, ts_end)
    key_cond_expr = "#place = :place_id and #ts BETWEEN :ts_start AND :ts_end"
    expr_names = {
        "#place": "place",
        "#ts": "ts",
    }
    expr_attr = {
        ":place_id": {
            "S": primary_key},
        ":ts_start": {
            "N": str(int(ts_start)*1000 - 7200000)},
        ":ts_end": {
            "N": str(int(ts_end)*1000 - 7200001)},
    }
    print("DEBUG", primary_key)
    list_reviews = get_from_dynamo_with_index_with_limit(comments_db, "PlaceByTs", key_cond_expr, expr_names, expr_attr, 100)
    _reviews = list()
    for review in list_reviews:
        timestamp = int(review.get('ts', {}).get('N', '0'))
        review_data = {
            "rate": float(review.get('rate', {}).get('N', '-1')),
            "review": review.get('review', {}).get('S', '-'),
            "platform": review.get('platform', {}).get('S', '-'),
            "timestamp": timestamp,
            "sentiment": review.get('sentiment', {}).get('S'),
            "features": review.get('features', {}).get('S'),
            "rate_ai": review.get('rate_ai', {}).get('N'),
            "date": (datetime.fromtimestamp(timestamp/1000) + timedelta(hours=2)).strftime('%Y/%m/%d, %H:%M:%S')
        }
        if review["platform"].get('S') == "trip_advisor":
            review_data["title"] = review.get('title', {}).get('S')
        _reviews.append(review_data)

    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(_reviews)
    }

def get_reviews_history(event):
    body = json.loads(event.get("body", "{}"))
    primary_key = f'{body.get("place_id")}-{body.get("restaurant_id")}'
    key_cond_expr = "#place = :place_id"
    expr_names = {
        "#place": "place"
    }
    expr_attr = {
        ":place_id": {
            "S": primary_key},
    }
    list_reviews = get_from_dynamo(reviews_history_db, key_cond_expr, expr_names, expr_attr)
    reviews_dict = dict()
    print(list_reviews)
    for review in list_reviews:
        if review.get('detail', {}).get('S', None) is None:
            continue
        year, month, day, platform = review["detail"].get('S', -1).split('-', 3)
        year, month, day = int(year), int(month), int(day)
        reviews_dict[year] = reviews_dict.get(year, dict())
        reviews_dict[year][month] = reviews_dict[year].get(month, dict())
        reviews_dict[year][month][day] = reviews_dict[year][month].get(day, dict())
        count = int(review.get('num_reviews', {}).get('N', '-1'))
        mean = float(review.get('mean_reviews', {}).get('N', '-1'))
        reviews_dict[year][month][day][platform] = {
            "count": count if count >= 0 else None,
            "mean": mean if mean >= 0 else None,
            "date": datetime.fromtimestamp(int(review.get('ts', {}).get('N', '0'))/1000).strftime('%Y/%m/%d')
        }

    years = list(reviews_dict.keys())
    trip_advisor_counts = []
    trip_advisor_means = []
    google_maps_counts = []
    google_maps_means = []
    for year in years:
        months = list(reviews_dict[year])
        for month in months:
            days = list(reviews_dict[year][month])
            for day in days:
                for platform in reviews_dict[year][month][day].keys():
                    if platform == 'trip_advisor':
                        trip_advisor_counts.append({"y": reviews_dict[year][month][day][platform]["count"], "x":reviews_dict[year][month][day][platform]["date"]})
                        trip_advisor_means.append({"y": reviews_dict[year][month][day][platform]["mean"], "x":reviews_dict[year][month][day][platform]["date"]})
                    elif platform == 'google-maps':
                        google_maps_counts.append({"y": reviews_dict[year][month][day][platform]["count"], "x":reviews_dict[year][month][day][platform]["date"]})
                        google_maps_means.append({"y":reviews_dict[year][month][day][platform]["mean"], "x":reviews_dict[year][month][day][platform]["date"]})

    res = {
        "trip_advisor": {
            "counts": trip_advisor_counts,
            "means": trip_advisor_means
        },
        "google_maps": {
            "counts": google_maps_counts,
            "means": google_maps_means
        }
    }

    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(res)
    }

def get_reviews_statistics(event):
    body = json.loads(event.get("body", "{}"))
    place_id, restaurant_id = body.get("place_id"), body.get("restaurant_id")
    key_cond_expr = "#place = :place_id and #restaurant = :restaurant_id"
    expr_names = {
        "#place": "ta_place_id",
        "#restaurant": "ta_restaurant_id"
    }
    expr_attr = {
        ":place_id": {
            "S": place_id},
        ":restaurant_id": {
            "S": restaurant_id},
    }
    list_ = get_from_dynamo(reviews_statistics_db, key_cond_expr, expr_names, expr_attr)
    stats = list_[0]
    res = {}
    res["gm_count"] = stats.get("gm_count", {}).get("N")
    res["gm_mean"] = stats.get("gm_mean", {}).get("N")
    res["ta_count"] = stats.get("ta_count", {}).get("N")
    res["ta_mean"] = stats.get("ta_mean", {}).get("N")
    res["rates"] = stats.get("rates", {}).get("S")
    res["features"] = stats.get("features", {}).get("S")
    res["sentiment"] = stats.get("sentiment", {}).get("S")
    res["ia_count"] = stats.get("ia_count", {}).get("N")
    res["ia_mean"] = stats.get("ia_mean", {}).get("N")

    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(res)
    }
