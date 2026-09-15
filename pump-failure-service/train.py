# Load the primary real-world sensor file
extract_path = './ai4i'
csv_file = os.path.join(extract_path, 'ai4i2020.csv')
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
    print(f"Loaded {df.shape[0]:,} predictive maintenance rows!")

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from lightgbm import LGBMClassifier
from sklearn.metrics import classification_report, confusion_matrix

# 2. Extract verified features and targets
# Dropping non-predictive IDs and the multi-class columns to focus on binary failure
X = df[['Air temperature [K]', 'Process temperature [K]', 'Rotational speed [rpm]', 'Torque [Nm]', 'Tool wear [min]']]
y = df['Machine failure'] # Clear target label: 0 for healthy, 1 for failed

# 3. Handle data split (Stratified since failure states are rare in industry)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 4. Standardize sensor scales
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. Train model with class weighting to handle structural imbalance
model = LGBMClassifier(n_estimators=100, scale_pos_weight=5, random_state=42)
model.fit(X_train_scaled, y_train)

# 6. Evaluate
y_pred = model.predict(X_test_scaled)
print("\n--- Verified Production Failure Model Report ---")
print(classification_report(y_test, y_pred))

import joblib

# Define the file paths where you want to save the artifacts
model_filename = 'pump_failure_model.pkl'
scaler_filename = 'pump_sensor_scaler.pkl'

# Save the trained model to disk
joblib.dump(model, model_filename)
print(f"Model successfully saved to: {model_filename}")

# Save the scaler artifact to disk
joblib.dump(scaler, scaler_filename)
print(f"Scaler successfully saved to: {scaler_filename}")
