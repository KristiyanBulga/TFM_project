import json
import boto3
from datetime import datetime, timedelta

stage = "dev"
region = "us-east-1"
dynamodb = boto3.client('dynamodb', region_name=region)
restaurants = ["g187486-d11938465", "g187486-d13971160"]
main_route = "C:\\Users\\krist\\Documents\\Git\\TFM_project\\reviews\\data"
day_in_miliseconds = 86400000

def restore_reviews_history(restaurant):
    key_cond_expr = "#place = :place_id"
    expr_names = {
        "#place": "place"
    }
    expr_attr = {
        ":place_id": {
            "S": restaurant},
    }
    list_reviews = dynamodb.query(
        TableName=f"comments-db-{stage}",
        IndexName="PlaceByTs",
        KeyConditionExpression=key_cond_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_attr,
        ScanIndexForward=True,
        # Limit=3
    ).get('Items')
    first_ts = int(list_reviews[0]['ts']['N'])
    first_time = datetime.fromtimestamp(first_ts/1000)
    day_start = first_time.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()*1000
    day_end = (first_time + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()*1000
    today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()*1000
    
    ta_mean, ta_count, gm_mean, gm_count, total_reviews = 0, 0, 0, 0, 0
    rates = {"real": {"trip_advisor": {str(n): 0 for n in range(1,6)}, "google_maps": {str(n): 0 for n in range(1,6)}}, "ai": {"trip_advisor": {str(n): 0 for n in range(1,6)}, "google_maps": {str(n): 0 for n in range(1,6)}}}
    features = {"positive": {}, "negative": {}}
    sentiment = {'positivo': 0, 'negativo':0, 'neutral': 0, 'desconocido': 0}
    ia_count, ia_mean = 0, 0
    i = 0
    while i < len(list_reviews) and day_start < today:
        review = list_reviews[i]
        ts = int(review['ts']['N'])
        # Is in this day
        # print(day_start, ts, day_end)
        if day_start <= ts and ts < day_end:
            if review['platform']['S'] == "trip_advisor":
                ta_mean += float(review['rate']['N'])
                ta_count += 1
                total_reviews += 1
            elif review['platform']['S'] == "google_maps":
                gm_mean += float(review['rate']['N'])
                gm_count += 1
                total_reviews += 1
            rates['real'][review['platform']['S']][review['rate']['N']] += 1
            if review.get('rate_ai', {}).get('N') and review.get('rate_ai', {}).get('N') != '-1':
                rates['ai'][review['platform']['S']][review['rate_ai']['N']] += 1
                if int(review['rate_ai']['N']) > 0:
                    ia_mean += int(review['rate_ai']['N'])
                    ia_count += 1
            if review.get('features', {}).get('S'):
                feat = json.loads(review.get('features', {}).get('S'))
                for x in feat["positive_words"]:
                    features["positive"][x] = features["positive"].get(x, 0) + 1
                for x in feat["negative_words"]:
                    features["negative"][x] = features["negative"].get(x, 0) + 1
            if review.get('sentiment').get('S'):
                sentiment[review.get('sentiment').get('S')] += 1
            i += 1
        else:
            if ta_count != 0 or gm_count != 0:
                ta_mean /= ta_count if ta_count else 1
                gm_mean /= gm_count if gm_count else 1
                print(ta_mean, ta_count, gm_mean, gm_count, datetime.fromtimestamp(day_start/1000).strftime('%Y/%m/%d'), day_start)
                # Store in history:
                date = datetime.fromtimestamp(day_start/1000).strftime('%Y-%m-%d')
                if gm_count:
                    key = {
                        'place': {'S': f"{restaurant}"},
                        'detail': {'S': f"{date}-google-maps"}
                    }
                    upd_expr = 'SET num_reviews = :rvw_num, mean_reviews = :rvw_mean, platform = :rvw_platform, ts = :rvw_timestamp'
                    expression_attr = {
                        ':rvw_num': {'N': str(gm_count)},
                        ':rvw_mean': {'N': str(gm_mean)},
                        ':rvw_platform': {'S': "google_maps"},
                        ':rvw_timestamp': {'N': str(day_start + 39600000)}
                    }
                    dynamodb.update_item(
                        TableName=f"reviews-history-db-{stage}",
                        Key=key,
                        UpdateExpression=upd_expr,
                        ExpressionAttributeValues=expression_attr
                    )
                if ta_count:
                    key = {
                        'place': {'S': f"{restaurant}"},
                        'detail': {'S': f"{date}-trip_advisor"}
                    }
                    upd_expr = 'SET num_reviews = :rvw_num, mean_reviews = :rvw_mean, platform = :rvw_platform, ts = :rvw_timestamp'
                    expression_attr = {
                        ':rvw_num': {'N': str(ta_count)},
                        ':rvw_mean': {'N': str(ta_mean)},
                        ':rvw_platform': {'S': "trip_advisor"},
                        ':rvw_timestamp': {'N': str(day_start + 39600000)}
                    }
                    dynamodb.update_item(
                        TableName=f"reviews-history-db-{stage}",
                        Key=key,
                        UpdateExpression=upd_expr,
                        ExpressionAttributeValues=expression_attr
                    )

                # UPDATE statistics
                key_cond_expr = "#place = :place_id and #restaurant = :restaurant_id"
                expr_names = {
                    "#place": "ta_place_id",
                    "#restaurant": "ta_restaurant_id"
                }
                expr_attr = {
                    ":place_id": {
                        "S": restaurant.split("-")[0]},
                    ":restaurant_id": {
                        "S": restaurant.split("-")[1]},
                }
                history = dynamodb.query(
                    TableName=f"reviews-statistics-db-{stage}",
                    KeyConditionExpression=key_cond_expr,
                    ExpressionAttributeNames=expr_names,
                    ExpressionAttributeValues=expr_attr,
                    ScanIndexForward=True,
                    # Limit=1
                ).get('Items')


                db_ta_mean, db_ta_count, db_gm_mean, db_gm_count = 0, 0, 0, 0
                db_ia_mean, db_ia_count = 0, 0,
                if history:
                    db_ta_mean = float(history[0]["ta_mean"]["N"])
                    db_ta_count = int(history[0]["ta_count"]["N"])
                    db_gm_mean = float(history[0]["gm_mean"]["N"])
                    db_gm_count = int(history[0]["gm_count"]["N"])
                    db_ia_mean = float(history[0]["ia_mean"]["N"])
                    db_ia_count = int(history[0]["ia_count"]["N"])
                    saved_rates = json.loads(history[0].get("rates", {}).get("S", "{}"))
                    for platform in ["trip_advisor", "google_maps"]:
                        for state in ["real", "ai"]:
                            for n in range(1,6):
                                rates[state][platform][str(n)] += saved_rates.get(state, {}).get(platform,{}).get(str(n), 0)
                    saved_features = json.loads(history[0].get("features", {}).get("S", json.dumps({"positive":{}, "negative": {}})))
                    for mood in ["positive", "negative"]:
                        for feature in features[mood]:
                            saved_features[mood][feature] = saved_features[mood].get(feature, 0) + features[mood][feature]
                    saved_sentiment = json.loads(history[0].get("sentiment", {}).get("S", json.dumps({'positivo': 0, 'negativo':0, 'neutral': 0, 'desconocido': 0})))
                    for mood in ['positivo', 'negativo', 'neutral', 'desconocido']:
                        saved_sentiment[mood] += sentiment[mood]
                else:
                    saved_features = features
                    saved_sentiment = sentiment

                db_ta_mean = (db_ta_mean * db_ta_count + ta_mean * ta_count) / ((db_ta_count + ta_count) if db_ta_count + ta_count else 1)
                db_ta_count += ta_count
                db_gm_mean = (db_gm_mean * db_gm_count + gm_mean * gm_count) / ((db_gm_count + gm_count) if db_gm_count + gm_count else 1)
                db_gm_count += gm_count
                ia_mean /= ia_count if ia_count else 1
                db_ia_mean = (db_ia_mean * db_ia_count + ia_mean * ia_count) / ((db_ia_count + ia_count) if db_ia_count + ia_count else 1)
                db_ia_count += ia_count

                key = {
                    'ta_place_id': {'S': restaurant.split("-")[0]},
                    'ta_restaurant_id': {'S': restaurant.split("-")[1]}
                }
                upd_expr = 'SET ta_mean = :ta_mean, ta_count = :ta_count, gm_mean = :gm_mean, gm_count = :gm_count, rates = :rates, features = :features, sentiment = :sentiment, ia_mean = :ia_mean, ia_count = :ia_count'
                expression_attr = {
                    ':ta_mean': {'N': str(db_ta_mean)},
                    ':ta_count': {'N': str(db_ta_count)},
                    ':gm_mean': {'N': str(db_gm_mean)},
                    ':gm_count': {'N': str(db_gm_count)},
                    ':rates': {"S": json.dumps(rates)},
                    ':features': {"S": json.dumps(saved_features)},
                    ':sentiment': {"S": json.dumps(saved_sentiment)},
                    ':ia_mean': {'N': str(db_ia_mean)},
                    ':ia_count': {'N': str(db_ia_count)},
                }
                dynamodb.update_item(
                    TableName=f"reviews-statistics-db-{stage}",
                    Key=key,
                    UpdateExpression=upd_expr,
                    ExpressionAttributeValues=expression_attr
                )

                ta_mean, ta_count, gm_mean, gm_count = 0, 0, 0, 0
                rates = {"real": {"trip_advisor": {str(n): 0 for n in range(1,6)}, "google_maps": {str(n): 0 for n in range(1,6)}}, "ai": {"trip_advisor": {str(n): 0 for n in range(1,6)}, "google_maps": {str(n): 0 for n in range(1,6)}}}
                features = {"positive": {}, "negative": {}}
                sentiment = {'positivo': 0, 'negativo':0, 'neutral': 0, 'desconocido': 0}
                ia_count, ia_mean = 0, 0

            day_start = (datetime.fromtimestamp(day_start/1000) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()*1000
            day_end = (datetime.fromtimestamp(day_end/1000) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()*1000
    print(i, len(list_reviews), day_start, today)
    if ta_count != 0 or gm_count != 0:
        ta_mean /= ta_count if ta_count else 1
        gm_mean /= gm_count if gm_count else 1
        print(ta_mean, ta_count, gm_mean, gm_count, datetime.fromtimestamp(day_start/1000).strftime('%Y/%m/%d'), day_start)
        date = datetime.fromtimestamp(day_start/1000).strftime('%Y-%m-%d')
        if gm_count:
            key = {
                'place': {'S': f"{restaurant}"},
                'detail': {'S': f"{date}-google-maps"}
            }
            upd_expr = 'SET num_reviews = :rvw_num, mean_reviews = :rvw_mean, platform = :rvw_platform, ts = :rvw_timestamp'
            expression_attr = {
                ':rvw_num': {'N': str(gm_count)},
                ':rvw_mean': {'N': str(gm_mean)},
                ':rvw_platform': {'S': "google_maps"},
                ':rvw_timestamp': {'N': str(day_start + 39600000)}
            }
            dynamodb.update_item(
                TableName=f"reviews-history-db-{stage}",
                Key=key,
                UpdateExpression=upd_expr,
                ExpressionAttributeValues=expression_attr
            )
        if ta_count:
            key = {
                'place': {'S': f"{restaurant}"},
                'detail': {'S': f"{date}-trip_advisor"}
            }
            upd_expr = 'SET num_reviews = :rvw_num, mean_reviews = :rvw_mean, platform = :rvw_platform, ts = :rvw_timestamp'
            expression_attr = {
                ':rvw_num': {'N': str(ta_count)},
                ':rvw_mean': {'N': str(ta_mean)},
                ':rvw_platform': {'S': "trip_advisor"},
                ':rvw_timestamp': {'N': str(day_start + 39600000)}
            }
            dynamodb.update_item(
                TableName=f"reviews-history-db-{stage}",
                Key=key,
                UpdateExpression=upd_expr,
                ExpressionAttributeValues=expression_attr
            )

        # UPDATE statistics
        key_cond_expr = "#place = :place_id and #restaurant = :restaurant_id"
        expr_names = {
            "#place": "ta_place_id",
            "#restaurant": "ta_restaurant_id"
        }
        expr_attr = {
            ":place_id": {
                "S": restaurant.split("-")[0]},
            ":restaurant_id": {
                "S": restaurant.split("-")[1]},
        }
        history = dynamodb.query(
            TableName=f"reviews-statistics-db-{stage}",
            KeyConditionExpression=key_cond_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_attr,
            ScanIndexForward=True,
            # Limit=1
        ).get('Items')


        db_ta_mean, db_ta_count, db_gm_mean, db_gm_count = 0, 0, 0, 0
        db_ia_mean, db_ia_count = 0, 0,
        if history:
            db_ta_mean = float(history[0]["ta_mean"]["N"])
            db_ta_count = int(history[0]["ta_count"]["N"])
            db_gm_mean = float(history[0]["gm_mean"]["N"])
            db_gm_count = int(history[0]["gm_count"]["N"])
            db_ia_mean = float(history[0]["ia_mean"]["N"])
            db_ia_count = int(history[0]["ia_count"]["N"])
            saved_rates = json.loads(history[0].get("rates", {}).get("S", "{}"))
            for platform in ["trip_advisor", "google_maps"]:
                for state in ["real", "ai"]:
                    for n in range(1,6):
                        rates[state][platform][str(n)] += saved_rates.get(state, {}).get(platform,{}).get(str(n), 0)
            saved_features = json.loads(history[0].get("features", {}).get("S", json.dumps({"positive":{}, "negative": {}})))
            for mood in ["positive", "negative"]:
                for feature in features[mood]:
                    saved_features[mood][feature] = saved_features[mood].get(feature, 0) + features[mood][feature]
            saved_sentiment = json.loads(history[0].get("sentiment", {}).get("S", json.dumps({'positivo': 0, 'negativo':0, 'neutral': 0, 'desconocido': 0})))
            for mood in ['positivo', 'negativo', 'neutral', 'desconocido']:
                saved_sentiment[mood] += sentiment[mood]
        else:
            saved_features = features
            saved_sentiment = sentiment

        db_ta_mean = (db_ta_mean * db_ta_count + ta_mean * ta_count) / ((db_ta_count + ta_count) if db_ta_count + ta_count else 1)
        db_ta_count += ta_count
        db_gm_mean = (db_gm_mean * db_gm_count + gm_mean * gm_count) / ((db_gm_count + gm_count) if db_gm_count + gm_count else 1)
        db_gm_count += gm_count
        db_ia_mean = (db_ia_mean * db_ia_count + ia_mean * ia_count) / ((db_ia_count + ia_count) if db_ia_count + ia_count else 1)
        db_ia_count += ia_count

        key = {
            'ta_place_id': {'S': restaurant.split("-")[0]},
            'ta_restaurant_id': {'S': restaurant.split("-")[1]}
        }
        upd_expr = 'SET ta_mean = :ta_mean, ta_count = :ta_count, gm_mean = :gm_mean, gm_count = :gm_count, rates = :rates, features = :features, sentiment = :sentiment, ia_mean = :ia_mean, ia_count = :ia_count'
        expression_attr = {
            ':ta_mean': {'N': str(db_ta_mean)},
            ':ta_count': {'N': str(db_ta_count)},
            ':gm_mean': {'N': str(db_gm_mean)},
            ':gm_count': {'N': str(db_gm_count)},
            ':rates': {"S": json.dumps(rates)},
            ':features': {"S": json.dumps(saved_features)},
            ':sentiment': {"S": json.dumps(saved_sentiment)},
            ':ia_mean': {'N': str(db_ia_mean)},
            ':ia_count': {'N': str(db_ia_count)},
        }
        dynamodb.update_item(
            TableName=f"reviews-statistics-db-{stage}",
            Key=key,
            UpdateExpression=upd_expr,
            ExpressionAttributeValues=expression_attr
        )

        ta_mean, ta_count, gm_mean, gm_count = 0, 0, 0, 0
        rates = {"real": {"trip_advisor": {str(n): 0 for n in range(1,6)}, "google_maps": {str(n): 0 for n in range(1,6)}}, "ai": {"trip_advisor": {str(n): 0 for n in range(1,6)}, "google_maps": {str(n): 0 for n in range(1,6)}}}
        features = {"positive": {}, "negative": {}}
        sentiment = {'positivo': 0, 'negativo':0, 'neutral': 0, 'desconocido': 0}
        ia_count, ia_mean = 0, 0
    print("From:", len(list_reviews), ". Processed:", total_reviews)

restore_reviews_history(restaurant=restaurants[1])