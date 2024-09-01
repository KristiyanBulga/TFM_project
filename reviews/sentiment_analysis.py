import boto3
import openai
import pandas as pd
from datetime import datetime, timedelta

stage = "dev"
region = "us-east-1"
dynamodb = boto3.client('dynamodb', region_name=region)
restaurants = ["g187486-d11938465", "g187486-d13971160"]
main_route = "C:\\Users\\krist\\Documents\\Git\\TFM_project\\reviews\\data\\sentiment"
main_prompt = '''Dado una lista de 20 comentarios en español de un restaurante, realiza un análisis de sentimiento de cada una y proporciona la siguiente información en formato JSON de cada una (devuelve solamente el JSON y las listas en una linea. Importante: la respuesta debe estar en texto, no en formato codigo):
 * positive_words: Una lista de las características positivas del restaurante. Devuelve como máximo una lista con 10 características, seleccionando las más representativas del comentario.
 * negative_words: Una lista de las características positivas del restaurante. Devuelve como máximo una lista con 10 características, seleccionando las más representativas del comentario
 * sentiment: Clasificación del sentimiento del comentario (positivo, neutral o negativo).
 * score: Puntuación del 1 al 5 (donde 1 es muy negativo y 5 es muy positivo) que refleje la valoración general del comentario.
 * id: identificador del comentario, el identificador se especifica junto a la palabra Cometario

En el caso de que te haya un comentario como el siguiente ("""EMPTY"""), devolver el objeto JSON para esa review: {"sentiment": "desconocido"}.
No te saltes ningún comentario. Analizalos todos.

Comentarios:

'''


# def get_sentiment_analysis(review:str, model="gpt-3.5-turbo"):
#     prompt = """Dado el siguiente comentario en español de un restaurante, realiza un análisis de sentimiento y proporciona la siguiente información en formato JSON (devuelve solamente el JSON):
#         * positive_words: Una lista de las características positivas del restaurante. Devuelve como máximo una lista con 10 características, seleccionando las más representativas del comentario.
#         * negative_words: Una lista de las características positivas del restaurante. Devuelve como máximo una lista con 10 características, seleccionando las más representativas del comentario
#         * sentiment: Clasificación del sentimiento del comentario (positivo, neutral o negativo).
#         * score: Puntuación del 1 al 5 (donde 1 es muy negativo y 5 es muy positivo) que refleje la valoración general del comentario.
#         * modelo: que modelo ha usado para realizar el sentiment analisis. Por ejemplo vader
#     """
#     prompt += f'Comentario: "{review}"'
#     messages = [{"role": "user", "content": prompt}]
#     response = openai.chat.completions.create(
#         model=model,
#         messages=messages,
#         temperature=0,
#     )
#     print(response)
#     return response.choices[0].message["content"]

def handler(event):
    restaurant = event["restaurant"]
    key_cond_expr = "#place = :place_id" # and (#sentiment = :positive or #sentiment = :neutral or #sentiment = :negative)"
    expr_names = {
        "#place": "place",
        # "#sentiment": "sentiment"
    }
    expr_attr = {
        ":place_id": {
            "S": restaurant},
        # ":positive": {
        #     "S": "positive"},
        # ":neutral": {
        #     "S": "neutral"},
        # ":negative": {
        #     "S": "negative"},
    }
    list_reviews = dynamodb.query(
        TableName=f"comments-db-{stage}",
        # IndexName="SentimentIndex",
        KeyConditionExpression=key_cond_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_attr,
        FilterExpression='attribute_not_exists(sentiment)',
        ScanIndexForward=True,
        # Limit=400
    ).get('Items')

    places, hashes, scores, texts, n_prompt = [], [], [], [], 0

    for review in list_reviews:
        places.append(review["place"]["S"])
        hashes.append(review["hash"]["S"])
        if review["review"]["S"].strip():
            texts.append(review["review"]["S"].replace("\n", ""))
        else:
            texts.append('EMPTY')
        scores.append(float(review["rate"]["N"]))
        if len(texts) == 20:
            with open(f"{main_route}\\{restaurant}\\{n_prompt}.txt", "w", encoding="utf8") as fp:
                revs = [f'Comentario {i}: """{texts[i]}"""' for i in range(len(texts)) ]
                fp.write(main_prompt + '[' + ',\n'.join(revs) + ']')
            texts = []
            n_prompt += 1
    
    if len(texts) != 0:
        with open(f"{main_route}\\{restaurant}\\{n_prompt}.txt", "w", encoding="utf8") as fp:
            revs = [f'Comentario {i}: """{texts[i]}"""' for i in range(len(texts)) ]
            fp.write(main_prompt + '[' + ',\n'.join(revs) + ']')
            texts = []
            n_prompt += 1

    df = pd.DataFrame({"place": places, "hash": hashes, "rate": scores})
    df.to_csv(f'{main_route}\\{restaurant}\\{restaurant}.csv', index=False)

event = {
    "restaurant": restaurants[1]
}

handler(event)