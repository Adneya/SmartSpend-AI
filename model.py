import pandas as pd
from sklearn.linear_model import LinearRegression

def predict_next_expense():

    data = {
        "month":[1,2,3,4,5,6],
        "expense":[12000,13500,14000,15000,16000,17000]
    }

    df = pd.DataFrame(data)

    X = df[["month"]]
    y = df["expense"]

    model = LinearRegression()
    model.fit(X,y)

    prediction = model.predict([[7]])

    return int(prediction[0])