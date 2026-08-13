/**
 * Bangus Buhai - IoT Aquaculture Monitoring System
 * Framework: Arduino
 * Target Board: Seeed Studio XIAO ESP32-S3
 * 
 * Dependencies:
 * - WiFi.h
 * - PubSubClient (by Nick O'Leary)
 * - OneWire (by Paul Stoffregen)
 * - DallasTemperature (by Miles Burton)
 * - LiquidCrystal I2C (by Frank de Brabander)
 * - ArduinoJson (by Benoit Blanchon)
 */

#include <WiFi.h>
#include <WiFiManager.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>

// --- PIN DEFINITIONS ---
// Board: Seeed Studio XIAO ESP32-S3
#define PIN_TURBIDITY   1  // Analog DFRobot Turbidity Sensor
#define PIN_DS18B20     2  // Temperature Sensor (requires 4.7kΩ pull-up)
#define PIN_RELAY       3  // 1-channel relay
#define I2C_SDA         5  // LCD SDA
#define I2C_SCL         6  // LCD SCL

// --- CONSTANTS & SETTINGS ---

// MQTT Config
const char* mqtt_server = "broker.hivemq.com"; // Default to public broker, change to your HiveMQ Cloud host
const int mqtt_port = 8883; // Secure MQTT
const char* device_id = "BB-AABBCC112233";
const char* mqtt_topic_telemetry = "bangusbuhai/devices/BB-AABBCC112233/telemetry";
const char* mqtt_topic_cmd = "bangusbuhai/devices/BB-AABBCC112233/cmd";

// --- GLOBAL OBJECTS ---
WiFiClientSecure espClient; 
PubSubClient mqttClient(espClient);
OneWire oneWire(PIN_DS18B20);
DallasTemperature sensors(&oneWire);
LiquidCrystal_I2C lcd(0x27, 16, 2); // I2C address 0x27, 16 columns, 2 rows

// --- GLOBAL VARIABLES ---
float ema_temp = 0.0f;
bool ema_temp_initialized = false;
float ema_turb = 0.0f;
bool ema_turb_initialized = false;

bool relay_state = false;
bool temperature_is_stale_or_failed = true;

uint32_t seq = 1;
int mqtt_reconnects = 0;

// Timing mechanisms for non-blocking loop
unsigned long last_sensor_read = 0;
unsigned long last_control_telemetry = 0;
const unsigned long SENSOR_INTERVAL = 2000;   // 2 seconds
const unsigned long CONTROL_INTERVAL = 5000;  // 5 seconds

// Function Prototypes
void setup_wifi();
void reconnect_mqtt();
void mqtt_callback(char* topic, byte* payload, unsigned int length);
void read_sensors();
void control_loop();
void publish_telemetry();
void update_lcd();
void turn_relay_on();
void turn_relay_off();

void setup() {
  Serial.begin(115200);

  // 1. Initialize Relay (Set to Safe State: OFF)
  pinMode(PIN_RELAY, OUTPUT);
  turn_relay_off(); 

  // 2. Initialize LCD
  Wire.begin(I2C_SDA, I2C_SCL);
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Bangus Buhai");
  lcd.setCursor(0, 1);
  lcd.print("Booting...");

  // 3. Initialize DS18B20 Sensor
  sensors.begin();

  // 4. Setup WiFi & MQTT
  setup_wifi();
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqtt_callback);

  lcd.clear();
}

void loop() {
  // MQTT Keep-alive and incoming message processing
  if (!mqttClient.connected()) {
    reconnect_mqtt();
  }
  mqttClient.loop();

  unsigned long current_millis = millis();

  /* --- TASK 1: Read Sensors & Update Display (Every 2 seconds) --- */
  if (current_millis - last_sensor_read >= SENSOR_INTERVAL) {
    last_sensor_read = current_millis;
    read_sensors();
    update_lcd();
  }

  /* --- TASK 2: Control Logic & MQTT Telemetry (Every 5 seconds) --- */
  if (current_millis - last_control_telemetry >= CONTROL_INTERVAL) {
    last_control_telemetry = current_millis;
    control_loop();
    publish_telemetry();
  }
}

/* --- SENSOR AGGREGATION & FILTERING LOGIC --- */
void read_sensors() {
  // 1. Read DS18B20 Temperature
  sensors.requestTemperatures();
  float raw_temp = sensors.getTempCByIndex(0);
  bool temp_ok = false;
  
  if (raw_temp >= 0.0f && raw_temp <= 60.0f) {
    temp_ok = true;
    temperature_is_stale_or_failed = false;
  } else {
    temperature_is_stale_or_failed = true;
  }

  // 2. Read Analog Turbidity
  // Note: ESP32-S3 default analogRead() is 12-bit (0-4095) representing 0-3.3V
  int raw_adc = analogRead(PIN_TURBIDITY);
  float raw_turb_mv = ((float)raw_adc / 4095.0f) * 3300.0f; 
  
  bool turb_ok = true;
  float raw_ntu = 0.0f;
  
  float voltage = raw_turb_mv / 1000.0f; 
  
  // CRITICAL FIX: Scale our 1.84V hardware max up to the expected 4.2V curve
  voltage = voltage * 2.28f;

  if (voltage < 2.5f) {
    raw_ntu = 3000.0f;
  } else if (voltage > 4.2f) {
    raw_ntu = 0.0f;
  } else {
    raw_ntu = -1120.4f * (voltage * voltage) + 5742.3f * voltage - 4352.9f;
  }

  // 3. Apply Exponential Moving Average (EMA) Filters
  if (temp_ok) {
    if (!ema_temp_initialized) {
      ema_temp = raw_temp;
      ema_temp_initialized = true;
    } else {
      ema_temp = (0.2f * raw_temp) + (0.8f * ema_temp);
    }
  }
  
  if (turb_ok) {
    if (!ema_turb_initialized) {
      ema_turb = raw_ntu;
      ema_turb_initialized = true;
    } else {
      ema_turb = (0.1f * raw_ntu) + (0.9f * ema_turb);
    }
  }
}

/* --- CONTROL & HYSTERESIS LOGIC --- */
void control_loop() {
  if (temperature_is_stale_or_failed) {
    turn_relay_off(); // Safe state
    return;
  }

  // Hysteresis Logic
  if (!relay_state && ema_temp >= 32.5f) {
    turn_relay_on();
  } else if (relay_state && ema_temp <= 31.0f) {
    turn_relay_off();
  }
}

void turn_relay_on() {
  digitalWrite(PIN_RELAY, HIGH);
  relay_state = true;
}

void turn_relay_off() {
  digitalWrite(PIN_RELAY, LOW);
  relay_state = false;
}

/* --- MQTT TELEMETRY JSON PUBLISH --- */
void publish_telemetry() {
  if (!mqttClient.connected()) return;

  // Use DynamicJsonDocument for ArduinoJson v6 or JsonDocument for v7.
  // Using StaticJsonDocument for robust memory allocation on stack (v6 standard).
  StaticJsonDocument<512> doc;
  
  doc["device_id"] = device_id;
  doc["tank_id"] = 1;
  doc["seq"] = seq++;
  doc["fw_version"] = "1.0.0-arduino";
  doc["uptime_s"] = millis() / 1000;
  
  JsonObject readings = doc.createNestedObject("readings");
  readings["temperature"] = ema_temp_initialized ? (round(ema_temp * 10.0) / 10.0) : 0.0;
  readings["turbidity"] = ema_turb_initialized ? (round(ema_turb * 10.0) / 10.0) : 0.0;
  readings["ph"] = 7.8; // Stubbed based on requirement
  readings["ph_source"] = "default";
  readings["relay_on"] = relay_state;
  
  JsonObject system = doc.createNestedObject("system");
  system["free_heap"] = ESP.getFreeHeap();
  system["wifi_rssi"] = WiFi.RSSI();
  system["mqtt_reconnects"] = mqtt_reconnects;

  char jsonBuffer[512];
  serializeJson(doc, jsonBuffer);
  
  mqttClient.publish(mqtt_topic_telemetry, jsonBuffer);
}

/* --- MQTT COMMAND RECEPTION --- */
void mqtt_callback(char* topic, byte* payload, unsigned int length) {
  // Topic: bangusbuhai/devices/{device_id}/cmd
  // Expected Payload: {"relay": "heater", "state": true}
  
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, payload, length);
  
  if (error) {
    Serial.print(F("deserializeJson() failed: "));
    Serial.println(error.c_str());
    return;
  }
  
  if (doc.containsKey("relay") && doc.containsKey("state")) {
    const char* relay_name = doc["relay"];
    bool state = doc["state"];
    
    if (strcmp(relay_name, "heater") == 0) {
      if (state) {
        turn_relay_on();
      } else {
        turn_relay_off();
      }
      Serial.print("MQTT Command: Relay overridden to ");
      Serial.println(state ? "ON" : "OFF");
    }
  }
}

/* --- WIFI SETUP --- */
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.println("Starting WiFi Provisioning...");

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi Setup AP");
  lcd.setCursor(0, 1);
  lcd.print("Connect to AP...");

  WiFiManager wm;
  // wm.resetSettings(); // Uncomment to wipe settings for testing
  
  // Creates a captive portal named "BangusBuhai_AP" with password "bangus123"
  bool res = wm.autoConnect("BangusBuhai_AP", "bangus123");

  if (!res) {
    Serial.println("Failed to connect to WiFi");
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("WiFi Failed!");
    delay(3000);
    // Let it continue without WiFi, will retry later or can call ESP.restart()
  } else {
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    
    // Set secure client to insecure to skip certificate validation 
    // This allows it to connect to HiveMQ Cloud without needing to store root CAs
    espClient.setInsecure(); 
  }
}

/* --- MQTT RECONNECT LOGIC --- */
void reconnect_mqtt() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    // Connect with device_id
    if (mqttClient.connect(device_id)) {
      Serial.println("connected");
      // Subscribe to command topic once connected
      mqttClient.subscribe(mqtt_topic_cmd);
    } else {
      Serial.print("failed, rc=");
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      
      mqtt_reconnects++;
      
      // Non-blocking 5 second delay approximation during reconnect
      unsigned long start = millis();
      while (millis() - start < 5000) {
        delay(1);
      }
    }
  }
}

/* --- LCD DISPLAY UPDATE --- */
void update_lcd() {
  lcd.clear();
  
  // Row 0: Sensors
  lcd.setCursor(0, 0);
  if (temperature_is_stale_or_failed) {
    lcd.print("T:ERR ");
  } else {
    lcd.print("T:");
    lcd.print(ema_temp, 1);
    lcd.print("C ");
  }
  
  lcd.print("NTU:");
  lcd.print(ema_turb, 0);
  
  // Row 1: System Status
  lcd.setCursor(0, 1);
  if (WiFi.status() == WL_CONNECTED && mqttClient.connected()) {
    lcd.print("W:OK M:OK");
  } else {
    lcd.print("W:");
    lcd.print(WiFi.status() == WL_CONNECTED ? "OK" : "XX");
    lcd.print(" M:");
    lcd.print(mqttClient.connected() ? "OK" : "XX");
  }
  
  lcd.print(" R:");
  lcd.print(relay_state ? "ON " : "OFF");
}
