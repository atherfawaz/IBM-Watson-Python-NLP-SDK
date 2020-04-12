import string

import pandas as pd
from . import test
from nltk.corpus import stopwords
from sklearn import naive_bayes
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.model_selection import train_test_split


def sarcasm_detector(statement):
    raw = pd.read_json('C:\\Users\\Wasiq\\PycharmProjects\\ibmwatson_python_sdk\\ibm_watson\\Integration\\Sarcasm\\Sarcasm_Headlines_Dataset.json', lines=True)
    raw.head(3)
    df = raw
    df.pop('article_link')
    df.dropna()
    df.head()

    X = df['headline']
    y = df['is_sarcastic']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

    stop_words = stopwords.words('english') + list(string.punctuation)
    vectorizer = CountVectorizer(lowercase=True, stop_words=stop_words)
    X_train = vectorizer.fit_transform(X_train)

    model = naive_bayes.MultinomialNB()
    model.fit(X_train, y_train)

    test_data = vectorizer.transform(X_test)
    y_predict = model.predict(test_data)
    statementList = [statement]
    predict_sample_data = vectorizer.transform(statementList)
    predicted = model.predict(predict_sample_data)

    if predicted == 1:

        return test.run_chat_bot(statement)
    else:
        return None

