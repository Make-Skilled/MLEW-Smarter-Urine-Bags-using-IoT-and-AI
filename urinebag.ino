#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ThingSpeak.h>
#include <WiFi.h>
#include <HTTPClient.h>

// Wi-Fi Credentials
const char *ssid = "tsr";
const char *password = "1234567890";

//// Flask Server URL
//const char *serverURL = "http://YOUR_FLASK_SERVER_IP:5000/data"; // Change to your Flask server IP

// ThingSpeak channel info
unsigned long channelID = 2215158;
const char *writeAPIKey = "3AMGXO1YIBDBQI8I";

// Define pins for sensors
#define TRIG_PIN 5
#define ECHO_PIN 4
#define TEMP_SENSOR_PIN 2
#define TURBIDITY_SENSOR_PIN 34

// Define pins for TCS3200 Color Sensor
#define S0 21
#define S1 22
#define S2 23
#define S3 19
#define SENSOR_OUT 18

// Initialize temperature sensor
OneWire oneWire(TEMP_SENSOR_PIN);
DallasTemperature sensors(&oneWire);

WiFiClient client;
HTTPClient http;

void setup() {
    Serial.begin(115200);

    // Connect to Wi-Fi
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.println("Connecting to WiFi...");
    }
    Serial.println("Connected to WiFi");

    // Connect to ThingSpeak
    ThingSpeak.begin(client);

    // Initialize sensors
    sensors.begin();
    pinMode(TRIG_PIN, OUTPUT);
    pinMode(ECHO_PIN, INPUT);

    // Initialize TCS3200 Color Sensor
    pinMode(S0, OUTPUT);
    pinMode(S1, OUTPUT);
    pinMode(S2, OUTPUT);
    pinMode(S3, OUTPUT);
    pinMode(SENSOR_OUT, INPUT);
    
    digitalWrite(S0, HIGH);
    digitalWrite(S1, LOW);
}

// Function to get Urine Volume using Ultrasonic Sensor
float getUrineVolume() {
    digitalWrite(TRIG_PIN, LOW);
    delayMicroseconds(2);
    digitalWrite(TRIG_PIN, HIGH);
    delayMicroseconds(10);
    digitalWrite(TRIG_PIN, LOW);

    long duration = pulseIn(ECHO_PIN, HIGH);
    float distance = (duration * 0.0343) / 2; // Convert to cm
    float volume = 100 - distance; // Example formula
    return volume;
}

// Function to get Urine Temperature
float getTemperature() {
    sensors.requestTemperatures();
    return sensors.getTempCByIndex(0);
}

// Function to get Turbidity Levels
int getTurbidity() {
    return analogRead(TURBIDITY_SENSOR_PIN);
}

// Function to Read Urine Color using TCS3200
int readColor(char color) {
    if (color == 'R') {
        digitalWrite(S2, LOW);
        digitalWrite(S3, LOW);
    } else if (color == 'G') {
        digitalWrite(S2, HIGH);
        digitalWrite(S3, HIGH);
    } else if (color == 'B') {
        digitalWrite(S2, LOW);
        digitalWrite(S3, HIGH);
    }

    delay(100);
    return pulseIn(SENSOR_OUT, LOW);
}

// Function to Analyze Urine Color Condition
String analyzeUrineColor(int red, int green, int blue) {
    if (red > green && red > blue) {
        return "Dehydration Risk (Dark Yellow)";
    } else if (green > red && green > blue) {
        return "Normal (Light Yellow)";
    } else if (blue > red && blue > green) {
        return "Possible Infection (Cloudy)";
    } else {
        return "Check Urine Sample";
    }
}

//// Function to send data to Flask Server
//void sendToFlask(float volume, float temperature, int turbidity, int red, int green, int blue) {
//    if (WiFi.status() == WL_CONNECTED) {
//        http.begin(serverURL);
//        http.addHeader("Content-Type", "application/json");
//
//        String jsonData = "{";
//        jsonData += "\"volume\":" + String(volume) + ",";
//        jsonData += "\"temperature\":" + String(temperature) + ",";
//        jsonData += "\"turbidity\":" + String(turbidity) + ",";
//        jsonData += "\"red\":" + String(red) + ",";
//        jsonData += "\"green\":" + String(green) + ",";
//        jsonData += "\"blue\":" + String(blue);
//        jsonData += "}";
//
//        int httpResponseCode = http.POST(jsonData);
//        Serial.println("Flask Server Response Code: " + String(httpResponseCode));
//
//        http.end();
//    } else {
//        Serial.println("WiFi Disconnected, Cannot Send Data to Flask Server!");
//    }
//}

void loop() {
    // Get Sensor Data
    float urineVolume = getUrineVolume();
    float temperature = getTemperature();
    int turbidity = getTurbidity();
    
    // Read Color Values
    int red = readColor('R');
    int green = readColor('G');
    int blue = readColor('B');
    
    String urineCondition = analyzeUrineColor(red, green, blue);

    // Print Data to Serial Monitor
    Serial.println("Urine Volume: " + String(urineVolume) + " mL");
    Serial.println("Temperature: " + String(temperature) + "°C");
    Serial.println("Turbidity: " + String(turbidity));
    Serial.println("Color - R: " + String(red) + " G: " + String(green) + " B: " + String(blue));
    Serial.println("Urine Condition: " + urineCondition);

    // Send Data to ThingSpeak
    ThingSpeak.setField(1, urineVolume);
    ThingSpeak.setField(2, temperature);
    ThingSpeak.setField(3, turbidity);
    ThingSpeak.setField(4, red);
    ThingSpeak.setField(5, green);
    ThingSpeak.setField(6, blue);
    ThingSpeak.setField(7,urineCondition);
    
    int statusCode = ThingSpeak.writeFields(channelID, writeAPIKey);
    if (statusCode == 200) {
        Serial.println("Data sent to ThingSpeak successfully!");
    } else {
        Serial.println("Error sending data to ThingSpeak. Status Code: " + String(statusCode));
    }
//    sendToFlask(urineVolume, temperature, turbidity, red, green, blue);
    delay(20000);
}
