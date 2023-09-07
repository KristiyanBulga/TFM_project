import boto3
import json
import logging
from datetime import datetime, timedelta
from utils.helper_wo_pandas import get_from_dynamo, comments_db, reviews_history_db

logging.getLogger().setLevel(logging.INFO)


def get_restaurant_reviews(event, amount: str = None):
    body = json.loads(event.get("body", "{}"))
    primary_key = f'{body.get("place_id")}-{body.get("restaurant_id")}'
    if amount == "last":
        today = datetime.today()
        last_friday = today - timedelta(days=today.weekday() + 10)
        key_cond_expr = "#place = :place_id and #ts > :timestamp"
        expr_names = {
            "#place": "place",
            "#ts": "timestamp"
        }
        expr_attr = {
            ":place_id": {
                "S": primary_key},
            ":timestamp": {
                "N": str(int(last_friday.timestamp() * 1000))}
        }
        print("DEBUG", primary_key, last_friday.timestamp() * 1000)
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
    trip_advisor_reviews = list()
    google_maps_reviews = list()
    for review in list_reviews:
        timestamp = int(review.get('timestamp', {}).get('N', '0'))
        review_data = {
            "rate": float(review.get('rate', {}).get('N', '-1')),
            "review": review.get('review', {}).get('S', '-'),
            "timestamp": timestamp,
            "date": datetime.fromtimestamp(timestamp/1000).strftime('%Y/%m/%d %H:%M:%S')
        }
        if review["platform"] == "trip_advisor":
            review_data["title"] = review.get('title', {}).get('S', '-')
            trip_advisor_reviews.append(review_data)
        else:
            google_maps_reviews.append(review_data)

    res = {
        "trip_advisor_reviews": trip_advisor_reviews,
        "google_maps_reviews": google_maps_reviews
    }
    return {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True,
        },
        "body": json.dumps(res)
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
        year, month, platform = review["detail"].get('S', -1).split('-')
        year = int(year)
        month = int(month)
        if reviews_dict.get(year, None) is None:
            reviews_dict[year] = dict()
        if reviews_dict[year].get(month, None) is None:
            reviews_dict[year][month] = dict()
        count = int(review.get('num_reviews', {}).get('N', '-1'))
        mean = float(review.get('mean_reviews', {}).get('N', '-1'))
        reviews_dict[year][month][platform] = {
            "count": count if count >= 0 else None,
            "mean": mean if mean >= 0 else None
        }

    years = list(reviews_dict.keys())
    trip_advisor_counts = []
    trip_advisor_means = []
    google_maps_counts = []
    google_maps_means = []
    for year in years:
        months = list(reviews_dict[year])
        for month in months:
            for platform in reviews_dict[year][month].keys():
                if platform == 'trip_advisor':
                    trip_advisor_counts.append(reviews_dict[year][month][platform]["count"])
                    trip_advisor_means.append(reviews_dict[year][month][platform]["mean"])
                elif platform == 'google_maps':
                    google_maps_counts.append(reviews_dict[year][month][platform]["count"])
                    google_maps_means.append(reviews_dict[year][month][platform]["mean"])

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
