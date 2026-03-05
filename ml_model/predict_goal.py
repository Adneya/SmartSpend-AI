import joblib
import numpy as np

# Load model
model = joblib.load("savings_model.pkl")

# User input
goal_amount = float(input("Enter your savings goal amount: "))

# Predict next 12 months savings
future_months = np.arange(6, 18).reshape(-1,1)

predicted_savings = model.predict(future_months)

print("\nPredicted monthly savings:")
print(predicted_savings)

# Calculate months required
total = 0
months = 0

for s in predicted_savings:
    total += s
    months += 1
    if total >= goal_amount:
        break

print("\nYou can reach your goal in:", months, "months")