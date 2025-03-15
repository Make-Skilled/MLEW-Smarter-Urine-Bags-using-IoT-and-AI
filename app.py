from flask import Flask, jsonify
import joblib
import numpy as np
import requests

# Load the trained model
model = joblib.load("urine.pkl")

# ThingSpeak channel configuration
THINGSPEAK_API_KEY = '3AMGXO1YIBDBQI8I'  # Replace with your ThingSpeak API key
CHANNEL_ID = '2215158'  # Replace with your ThingSpeak channel ID 2215158

# URL to fetch the latest data from the ThingSpeak API
THINGSPEAK_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json?api_key={THINGSPEAK_API_KEY}&results=1"  # Adjust field ID based on your setup

app = Flask(__name__)

@app.route("/")
def home():
    return "Welcome to the Urine UTI Risk Prediction API!"

@app.route("/predict", methods=["GET"])
def predict_uti():
    # Get the latest data from ThingSpeak API
    response = requests.get(THINGSPEAK_URL)
    data = response.json()
    print(data)
    if not data or "feeds" not in data or not data["feeds"]:
        return jsonify({"error": "No data available from ThingSpeak"})
    
    # Extract the values from the response
    latest_entry = data["feeds"][0]
    
    # Assuming your fields are:
    # field1: urine_volume, field2: temperature, field3: turbidity, field4: red, field5: green, field6: blue
    features = [
        float(latest_entry["field1"]),  # urine_volume
        float(latest_entry["field2"]),  # temperature
        float(latest_entry["field3"]),  # turbidity
        int(latest_entry["field4"]),    # red
        int(latest_entry["field5"]),    # green
        int(latest_entry["field6"])     # blue
    ]
    
    # Convert to numpy array and reshape for prediction
    features_array = np.array(features).reshape(1, -1)
    
    # Predict UTI risk (0 = Low, 1 = High)
    prediction = model.predict(features_array)[0]
    
    # Return the response
    return jsonify({"uti_risk": int(prediction)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
