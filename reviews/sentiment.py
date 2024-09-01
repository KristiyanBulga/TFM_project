from transformers import pipeline
from textblob import TextBlob
from textblob.sentiments import NaiveBayesAnalyzer,PatternAnalyzer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from flair.models import TextClassifier
classifier = TextClassifier.load('en-sentiment')
from flair.data import Sentence
from sklearn.metrics import accuracy_score
# import spacy
# nlp = spacy.load("es_core_news_sm") 
# sentiment_analyzer = nlp.create_pipe("sentiment_analyzer")
# nlp.add_pipe(sentiment_analyzer) 

def sentiment_analysis_01(review):
    sentiment_pipeline = pipeline("sentiment-analysis")
    data = [review]
    print(sentiment_pipeline(data))

def sentimet_textBlob(review):
    print(TextBlob(review, analyzer=NaiveBayesAnalyzer()).sentiment)

def vader_sentiment(review):
    sentiment = SentimentIntensityAnalyzer()
    print(sentiment.polarity_scores(review))

def sentiment_flair(review):
    sentence = Sentence(review)
    classifier.predict(sentence)
    score = sentence.labels[0].score
    value = sentence.labels[0].value
    print(score, value)

# def sentiment_spacy(review):
#     sentiment = sentiment_analyzer(review)
#     print(sentiment.sentiment, sentiment.confidence, sentiment.tokens)

def main(review):
    sentiment_analysis_01(review)
    # sentimet_textBlob(review)
    vader_sentiment(review)
    sentiment_flair(review)


review_01 = "Como siempre, todo lo que pidas está muy rico. Sorprendentes patatas bravas, llamadas Bravas Palencia. La tortillitas de camarones están muy buenas pero siempre me han parecido un poco bastas o gruesas. El lomo de orza y las croquetas, riquísimas. El tataki de atún bien sin más. Pero esta vez tengo que expresar una queja que no exprese en el instante porque éramos los últimos y cerraban ya el local, y con amigos no era el momento. En el ticket que adjunto nos cobran 1,5 € por cabeza en concepto Servicio de restaurante. Es decir, nos clavan 9 euros simplemente por hacer el trabajo propio de este local??? A qué extremo hemos llegado ya de abusos??? Por no hablar que ese concepto no figura en la carta, y, como bien es sabido, no se puede cobrar nada que no aparezca en la carta, y menos aún este concepto tan vergonzoso."
review_02 = "Nos ha atendido Manolo y ha sido muy amable y atento. Nos gustó mucho la fusión de la comida en Martina. La próxima vez que vengamos a Albacete repetiremos."

main(review_02)