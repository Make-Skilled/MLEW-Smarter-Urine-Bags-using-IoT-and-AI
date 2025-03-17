from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import joblib
import numpy as np
import requests
from datetime import datetime, timedelta

# Initialize Flask extensions
db = SQLAlchemy()
login_manager = LoginManager()

# ThingSpeak configuration
THINGSPEAK_API_KEY = '3AMGXO1YIBDBQI8I'
CHANNEL_ID = '2215158'
THINGSPEAK_BASE_URL = f"https://api.thingspeak.com/channels/{CHANNEL_ID}/feeds.json"

def calculate_uti_risk(feed_entry):
    """
    Calculate UTI risk based on sensor measurements
    Returns True if risk is high, False otherwise
    """
    try:
        # Get sensor values with proper error handling
        try:
            temperature = float(feed_entry.get("field2", 0))
            turbidity = float(feed_entry.get("field3", 0))
            red = int(float(feed_entry.get("field4", 0)))
            green = int(float(feed_entry.get("field5", 0)))
            blue = int(float(feed_entry.get("field6", 0)))
        except (ValueError, TypeError) as e:
            print(f"Error converting sensor values: {e}")
            return False

        # Define risk thresholds
        TEMP_THRESHOLD = 37.5  # °C
        TURBIDITY_THRESHOLD = 700  # NTU
        COLOR_THRESHOLD = 100  # RGB value

        # Calculate risk based on multiple factors
        risk_factors = [
            temperature > TEMP_THRESHOLD,  # High temperature
            turbidity > TURBIDITY_THRESHOLD,  # High turbidity
            green < COLOR_THRESHOLD,  # Low green value (possible infection)
            blue > red and blue > green  # Blue dominant color (cloudiness)
        ]

        # Return True if any two or more risk factors are present
        return sum(risk_factors) >= 2

    except Exception as e:
        print(f"Error in calculate_uti_risk: {e}")
        return False

def get_thingspeak_data(results=1):
    """Fetch data from ThingSpeak"""
    try:
        url = f"{THINGSPEAK_BASE_URL}?api_key={THINGSPEAK_API_KEY}&results={results}"
        response = requests.get(url)
        data = response.json()
        print("ThingSpeak Raw Data:", data)  # Debug print
        return data
    except Exception as e:
        print(f"Error fetching ThingSpeak data: {e}")
        return None

def process_measurement_data(feed_entry):
    try:
        # Convert and validate measurements
        urine_volume = float(feed_entry.get("field1", 0))
        temperature = float(feed_entry.get("field2", 0))
        turbidity = float(feed_entry.get("field3", 0))

        # Calculate UTI risk
        uti_risk = calculate_uti_risk(feed_entry)

        return {
            "timestamp": datetime.strptime(feed_entry["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
            "urine_volume": urine_volume,
            "temperature": temperature,
            "turbidity": turbidity,
            "uti_risk": uti_risk,
            "condition": feed_entry.get("field7", "Normal")
        }
    except Exception as e:
        print(f"Error in process_measurement_data: {e}")
        return None

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urine_monitoring.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    return app

# Create app instance
app = create_app()

# User loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Models
class UrineMeasurement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    urine_volume = db.Column(db.Float, nullable=False)
    temperature = db.Column(db.Float, nullable=False)
    turbidity = db.Column(db.Float, nullable=False)
    red = db.Column(db.Integer, nullable=False)
    green = db.Column(db.Integer, nullable=False)
    blue = db.Column(db.Integer, nullable=False)
    uti_risk = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        return {
            'timestamp': self.timestamp.isoformat(),
            'urine_volume': self.urine_volume,
            'temperature': self.temperature,
            'turbidity': self.turbidity,
            'color': {
                'red': self.red,
                'green': self.green,
                'blue': self.blue
            },
            'uti_risk': self.uti_risk
        }

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    measurements = db.relationship('UrineMeasurement', backref='user', lazy=True)

# Routes
@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Please check your login details and try again.')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email address already exists')
            return redirect(url_for('signup'))
            
        new_user = User(
            email=email,
            name=name,
            password=generate_password_hash(password, method='sha256')
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/measurements/latest')
@login_required
def get_latest_measurement():
    """Get the latest measurement data"""
    try:
        data = get_thingspeak_data(results=1)
        
        if not data or "feeds" not in data or not data["feeds"]:
            return jsonify({"error": "No data available from ThingSpeak"}), 404
        
        measurement_data = process_measurement_data(data["feeds"][0])
        print("Processed Measurement Data:", measurement_data)  # Debug print
        
        if measurement_data is None:
            return jsonify({"error": "Error processing measurement data"}), 500
            
        return jsonify(measurement_data)
        
    except Exception as e:
        print(f"Error in get_latest_measurement: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/measurements/historical", methods=["GET"])
@login_required
def get_historical_data():
    """Get historical measurement data"""
    try:
        timeframe = request.args.get('timeframe', '24h')
        
        # Calculate the start time based on the timeframe
        if timeframe == '24h':
            start_time = datetime.utcnow() - timedelta(hours=24)
            results = 24
        elif timeframe == '7d':
            start_time = datetime.utcnow() - timedelta(days=7)
            results = 168  # 7 days * 24 hours
        elif timeframe == '30d':
            start_time = datetime.utcnow() - timedelta(days=30)
            results = 720  # 30 days * 24 hours
        else:
            return jsonify({"error": "Invalid timeframe"}), 400

        # Get historical data from database
        measurements = UrineMeasurement.query.filter(
            UrineMeasurement.user_id == current_user.id,
            UrineMeasurement.timestamp >= start_time
        ).order_by(UrineMeasurement.timestamp.desc()).all()

        # If no data in database, fetch from ThingSpeak
        if not measurements:
            data = get_thingspeak_data(results=results)
            if data and "feeds" in data:
                measurements_data = [process_measurement_data(feed) for feed in data["feeds"]]
            else:
                measurements_data = []
        else:
            measurements_data = [measurement.to_dict() for measurement in measurements]

        return jsonify({
            "timeframe": timeframe,
            "measurements": measurements_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/measurements/stats", methods=["GET"])
@login_required
def get_measurement_stats():
    """Get statistical data for measurements"""
    try:
        # Get the last 24 hours of measurements
        start_time = datetime.utcnow() - timedelta(hours=24)
        measurements = UrineMeasurement.query.filter(
            UrineMeasurement.user_id == current_user.id,
            UrineMeasurement.timestamp >= start_time
        ).all()

        if measurements:
            stats = {
                "urine_volume": {
                    "avg": sum(m.urine_volume for m in measurements) / len(measurements),
                    "max": max(m.urine_volume for m in measurements),
                    "min": min(m.urine_volume for m in measurements)
                },
                "temperature": {
                    "avg": sum(m.temperature for m in measurements) / len(measurements),
                    "max": max(m.temperature for m in measurements),
                    "min": min(m.temperature for m in measurements)
                },
                "uti_risk_count": sum(1 for m in measurements if m.uti_risk),
                "total_measurements": len(measurements)
            }
        else:
            stats = {
                "urine_volume": {"avg": 0, "max": 0, "min": 0},
                "temperature": {"avg": 0, "max": 0, "min": 0},
                "uti_risk_count": 0,
                "total_measurements": 0
            }

        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
