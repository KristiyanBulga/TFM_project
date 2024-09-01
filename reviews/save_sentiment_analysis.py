from os import walk
import json
import boto3
import pandas as pd
from bs4 import BeautifulSoup as bs

stage = "dev"
region = "us-east-1"
dynamodb = boto3.client('dynamodb', region_name=region)
restaurants = ["g187486-d11938465", "g187486-d13971160"]
main_route = "C:\\Users\\krist\\Documents\\Git\\TFM_project\\reviews\\data\\sentiment"

def handler(event):
    restaurant = event["restaurant"]
    filenames = next(walk(f"{main_route}\\{restaurant}"), (None, None, []))[2]
    sentiments = []
    ai_scores = []
    features = []
    for filename in filenames:
        if filename.endswith(".html"):
            print(filename)
            with open(f"{main_route}\\{restaurant}\\{filename}", encoding="utf8") as fp:
                soup = bs(fp, 'html.parser')
                response_parent = soup.find_all("div", class_="markdown prose w-full break-words dark:prose-invert dark")
                print(f"{len(response_parent)} files found")
                for i in range(len(response_parent)):
                    json_obj = response_parent[i].find("p").contents[0]
                    reviews = json.loads(json_obj)
                    print(f"For response {i} there is {len(reviews)} sentiments")
                    for review in reviews:
                        sentiments.append(review.get("sentiment").lower().strip())
                        ai_scores.append(review.get("score", -1))
                        features.append({"positive_words": review.get("positive_words", []), "negative_words": review.get("negative_words", [])})
    df_analysis = pd.DataFrame({"sentiment": sentiments, "ai_rate": ai_scores, "features": features})
    df = pd.read_csv(f'{main_route}\\{restaurant}\\{restaurant}.csv')
    if df_analysis.shape[0] != df.shape[0]:
        return
    merged = df.merge(df_analysis, left_index=True, right_index=True)
    print(merged)
    input("Proceed? ...")
    input("Are u sure? ...")
    for i, row in merged.iterrows():
        key = {
            'place': {'S': row["place"]},
            'hash': {'S': row["hash"]}
        }
        upd_expr = 'SET sentiment = :sentiment, rate_ai = :rate_ai, features = :features'
        expression_attr = {
            ':sentiment': {'S': row["sentiment"]},
            ':rate_ai': {'N': str(row["ai_rate"])},
            ':features': {'S': json.dumps(row["features"])},
        }
        dynamodb.update_item(
            TableName=f"comments-db-{stage}",
            Key=key,
            UpdateExpression=upd_expr,
            ExpressionAttributeValues=expression_attr
        )
        print(f"Updated {i}")

event = {
    "restaurant": restaurants[1]
}

handler(event)