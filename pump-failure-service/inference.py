import joblib
import pandas as pd

# 1. Load the saved model and scaler artifacts
loaded_model = joblib.load('pump_failure_model.pkl')
loaded_scaler = joblib.load('pump_sensor_scaler.pkl')
print("Model and Scaler successfully loaded into production!")

# 2. Simulate incoming real-time sensor data from a pump
# Schema matches: Air temp, Process temp, Rotational speed, Torque, Tool wear
new_sensor_data = pd.DataFrame([{
    'Air temperature [K]': 300.2,
    'Process temperature [K]': 310.1,
    'Rotational speed [rpm]': 1450,
    'Torque [Nm]': 55.4,
    'Tool wear [min]': 125
}])

# 3. Transform the raw incoming data using the loaded scaler
scaled_data = loaded_scaler.transform(new_sensor_data)

# 4. Generate the prediction (0 = Normal, 1 = Failure)
prediction = loaded_model.predict(scaled_data)
prediction_probability = loaded_model.predict_proba(scaled_data)[:, 1]

print(f"Prediction: {'⚠️ FAILURE DETECTED' if prediction[0] == 1 else '✅ System Healthy'}")
print(f"Failure Probability: {prediction_probability[0]:.2%}")
