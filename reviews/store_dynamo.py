import pandas as pd
import hashlib
import boto3

stage = "dev"
region = "us-east-1"
dynamodb = boto3.client('dynamodb', region_name=region)
restaurants = ["g187486-d11938465", "g187486-d13971160"]
main_route = "C:\\Users\\krist\\Documents\\Git\\TFM_project\\reviews\\data"

def encode_to_hex(input_string):
    # Create a SHA-256 hash object
    sha256 = hashlib.sha256()
    # Update the hash object with the input string
    sha256.update(input_string.encode('utf-8'))
    # Get the hexadecimal digest of the hash
    hex_digest = sha256.hexdigest()
    # Return the first 12 characters of the hexadecimal digest
    return hex_digest

def store_reviews(restaurant):
    df = pd.read_csv(f'{main_route}\\{restaurant}.csv')
    for i, review in df.iterrows():
        key = {
            'place': {'S': f"{restaurant}"},
            'hash': {'S': encode_to_hex( review["title"] + review["content"])}
        }
        upd_expr = 'SET rate = :rvw_rate, title = :rvw_title, review = :rvw_text, platform = :rvw_platform, ts = :rvw_timestamp, category = :rvw_category'
        expression_attr = {
            ':rvw_rate': {'N': str(review["score"])},
            ':rvw_title': {'S': review["title"]},
            ':rvw_text': {'S': review["content"]},
            ':rvw_platform': {'S': "trip_advisor"},
            ':rvw_timestamp': {'N': str(review["ts"]*1000)},
            ':rvw_category': {'S': review["group"]}
        }
        # update_item_dynamo(comments_db, key, upd_expr, expression_attr)
        dynamodb.update_item(
            TableName=f"comments-db-{stage}",
            Key=key,
            UpdateExpression=upd_expr,
            ExpressionAttributeValues=expression_attr
        )
        print("Syncronized review", i)

store_reviews(restaurants[0])