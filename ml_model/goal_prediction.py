import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import joblib

# Load dataset
df = pd.read_csv("budget_data.csv")

df["date"] = pd.to_datetime(df["date"])
df["month"] = df["date"].dt.to_period("M")

# Monthly expenses
monthly_expense = df.groupby("month")["amount"].sum().reset_index()

# Assume monthly income
MONTHLY_INCOME = 60000

monthly_expense["savings"] = MONTHLY_INCOME - monthly_expense["amount"]

# Last 6 months
recent = monthly_expense.tail(6).copy()
recent["month_index"] = np.arange(len(recent))

X = recent[["month_index"]]
y = recent["savings"]

# Train model
model = LinearRegression()
model.fit(X, y)

# Accuracy
y_pred = model.predict(X)
r2 = r2_score(y, y_pred)

print("Model R2 Score:", r2)

# Save model
joblib.dump(model, "savings_model.pkl")

print("Model saved successfully!")