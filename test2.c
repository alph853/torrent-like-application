/* Basic Multi Threading Arduino Example
   This example code is in the Public Domain (or CC0 licensed, at your option.)
   Unless required by applicable law or agreed to in writing, this
   software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
   CONDITIONS OF ANY KIND, either express or implied.
*/
// Please read file README.md in the folder containing this example.
#include <Adafruit_NeoPixel.h>
#include <DHT20.h>
#include <LiquidCrystal_I2C.h>

/// package for connect to sever and mqtt
#include <WiFi.h>
#include "Adafruit_MQTT.h"
#include "Adafruit_MQTT_Client.h"
#include <Ultrasonic.h>

// Define pins

// Define sever
#define WLAN_SSID "RD-SEAI_2.4G"
#define WLAN_PASS "0305667542"

#define AIO_SERVER "mqtt.ohstem.vn"
#define AIO_SERVERPORT 1883
#define AIO_USERNAME "Jamwindow"
#define AIO_KEY "ẻ iogerio"

WiFiClient client;
Adafruit_MQTT_Client mqtt(&client, AIO_SERVER, AIO_SERVERPORT, AIO_USERNAME, AIO_USERNAME, AIO_KEY);
// Adafruit_MQTT_Client mqtt(&client, AIO_SERVER, AIO_SERVERPORT, AIO_USERNAME, AIO_USERNAME, AIO_KEY);

/****************************** Feeds ***************************************/
// send signal temperature to sever
Adafruit_MQTT_Publish temperature = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/V2");
Adafruit_MQTT_Publish luminosity = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/V3");
Adafruit_MQTT_Publish humidity = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/V1");
Adafruit_MQTT_Publish moisture = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/V4");
Adafruit_MQTT_Publish fan = Adafruit_MQTT_Publish(&mqtt, AIO_USERNAME "/feeds/V6");

// get the signal from sever
Adafruit_MQTT_Subscribe toggle = Adafruit_MQTT_Subscribe(&mqtt, AIO_USERNAME "/feeds/V5", MQTT_QOS_1);

#if CONFIG_FREERTOS_UNICORE
#define ARDUINO_RUNNING_CORE 0
#else
#define ARDUINO_RUNNING_CORE 1
#endif

#define ANALOG_INPUT_PIN 1
#define PIN GPIO_NUM_6 // Define the pin (adjust based on your board)
#define NUMPIXELS 4    // Define the number of NeoPixels

static uint32_t light = 0;
static uint32_t toggleValue = 0;
static int distance = 357;
void readToggle(uint32_t value)
{
    toggleValue = value;
}

// Define two tasks for Blink & AnalogRead.
void TaskBlink(void *pvParameters);
void TaskAnalogRead(void *pvParameters);
TaskHandle_t analog_read_task_handle; // You can (don't have to) use this to be able to manipulate a task from somewhere else.
void TaskTemperatureHumidity(void *pvParameters);
void TaskSoilMoistureAndRelay(void *pvParameters);
void TaskLightAndLED(void *pvParameters);
void TaskTurnOnLED(void *pvParameters);
void TaskDisAndFan(void *pvParameters);

void onoffcallback(uint32_t data)
{
    Serial.print("Hey we're in a onoff callback, the button value is: ");
    Serial.println(data);

    // Control LED based on toggle value
    if (data == 1)
    {
        digitalWrite(GPIO_NUM_48, HIGH);
    }
    else
    {
        digitalWrite(GPIO_NUM_48, LOW);
    }
}

void MQTT_connect()
{
    int8_t ret;

    // Stop if already connected.
    if (mqtt.connected())
    {
        return;
    }

    Serial.print("Connecting to MQTT... ");

    uint8_t retries = 3;
    while ((ret = mqtt.connect()) != 0)
    { // connect will return 0 for connected
        Serial.println(mqtt.connectErrorString(ret));
        Serial.println("Retrying MQTT connection in 10 seconds...");
        mqtt.disconnect();
        delay(10000); // wait 10 seconds
        retries--;
        if (retries == 0)
        {
            // basically die and wait for WDT to reset me
            while (1)
                ;
        }
    }
    Serial.println("MQTT Connected!");
}

// Define components here
Adafruit_NeoPixel pixels3(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel pixels5(4, GPIO_NUM_8, NEO_GRB + NEO_KHZ800);
DHT20 dht20;
LiquidCrystal_I2C lcd(33, 16, 2);
Ultrasonic ultrasonic(GPIO_NUM_18, GPIO_NUM_21);

// The setup function runs once when you press reset or power on the board.
void setup()
{

    // Initialize serial communication at 115200 bits per second:
    Serial.begin(115200);
    // Kết nối WiFi
    Serial.print("Connecting to WiFi...");
    WiFi.begin(WLAN_SSID);
    while (WiFi.status() != WL_CONNECTED)
    {
        delay(500);
        Serial.print(".");
    }

    Wire.begin(GPIO_NUM_11, GPIO_NUM_12);

    dht20.begin();
    lcd.begin();
    pixels3.begin();

    xTaskCreate(TaskBlink, "Task Blink", 2048, NULL, 2, NULL);
    xTaskCreate(TaskTemperatureHumidity, "Task Temperature", 2048, NULL, 2, NULL);
    xTaskCreate(TaskSoilMoistureAndRelay, "Task Soil Moisture", 2048, NULL, 2, NULL);
    xTaskCreate(TaskLightAndLED, "Task Light LED", 2048, NULL, 2, NULL);
    xTaskCreate(TaskDisAndFan, "Distance and fan", 2048, NULL, 2, NULL);

    // xTaskCreate(TaskTurnOnLED, "Task Turn On LED",2048, NULL, 2, NULL);

    Serial.printf("Basic Multi Threading Arduino Example\n");
    // Now the task scheduler, which takes over control of scheduling individual tasks, is automatically started.
    MQTT_connect();
    toggle.setCallback(onoffcallback);
}

void loop()
{
    MQTT_connect();
    mqtt.processPackets(10000);
    if (!mqtt.ping())
    {
        mqtt.disconnect();
    }
    delay(1000); // Delay a second between loops.
}

/*--------------------------------------------------*/
/*---------------------- Tasks ---------------------*/
/*--------------------------------------------------*/

void TaskDisAndFan(void *pvParameters)
{
    pinMode(GPIO_NUM_10, OUTPUT);
    uint32_t distance = 0;
    while (1)
    {
        Serial.print("Distance value: ");
        distance = ultrasonic.read();
        Serial.println(distance);
        analogWrite(GPIO_NUM_10, distance > 5 ? 0 : 100);
        vTaskDelay(2000);
    }
}

void TaskBlink(void *pvParameters)
{
    pinMode(GPIO_NUM_48, OUTPUT);
    while (1)
    {
        mqtt.subscribe(&toggle);
        vTaskDelay(500); // Add delay to prevent busy waiting
    }
}

void TaskTemperatureHumidity(void *pvParameters)
{

    while (1)
    {
        dht20.read();
        Serial.println(dht20.getTemperature());
        Serial.println(dht20.getHumidity());

        float temp = dht20.getTemperature();
        float hum = dht20.getHumidity();

        // Publish data to Adafruit IO
        //  temperatureFeed->save(temperature);
        //  humidityFeed->save(humidity);

        lcd.clear();
        lcd.setCursor(0, 0);
        lcd.print(dht20.getTemperature());
        lcd.setCursor(0, 1);
        lcd.print(dht20.getHumidity());

        // Gửi dữ liệu nhiệt độ lên MQTT
        if (temperature.publish(dht20.getTemperature()))
        {
            Serial.println(F("Temperature published successfully!"));
        }
        else
        {
            Serial.println(F("Failed to publish temperature"));
        }

        if (humidity.publish(dht20.getHumidity()))
        {
            Serial.println(F("Humidity published successfully!"));
        }
        else
        {
            Serial.println(F("Failed to publish humidity"));
        }

        vTaskDelay(5000);
    }
}

void TaskSoilMoistureAndRelay(void *pvParameters)
{
    while (1)
    {
        Serial.println(analogRead(GPIO_NUM_1));
        int soilMoisture = analogRead(GPIO_NUM_1);

        // Publish soil moisture data to Adafruit IO
        // soilMoistureFeed->save(soilMoisture);

        if (soilMoisture > 500)
        {
            digitalWrite(GPIO_NUM_6, LOW);
        }
        if (soilMoisture < 50)
        {
            digitalWrite(GPIO_NUM_6, HIGH);
        }

        int32_t moisture_value = analogRead(GPIO_NUM_1);
        Serial.print("Moisture value: ");
        if (moisture.publish(moisture_value))
        {
            Serial.println(F("Moisture published successfully!"));
        }
        else
        {
            Serial.println(F("Failed to publish Moisture"));
        }

        delay(9000);
    }
}

void TaskLightAndLED(void *pvParameters)
{
    while (1)
    {
        Serial.print("Light value: ");
        Serial.println(analogRead(GPIO_NUM_2));
        uint16_t lightValue = analogRead(GPIO_NUM_2);

        // LightFeed->save(lightValue);

        if (lightValue > 550)
        {
            pixels5.setPixelColor(0, pixels3.Color(255, 0, 0));
            pixels5.setPixelColor(1, pixels3.Color(255, 0, 0));
            pixels5.setPixelColor(2, pixels3.Color(255, 0, 0));
            pixels5.setPixelColor(3, pixels3.Color(255, 0, 0));
            pixels5.show();
        }
        if (lightValue < 350)
        {
            pixels5.setPixelColor(0, pixels3.Color(0, 0, 0));
            pixels5.setPixelColor(1, pixels3.Color(0, 0, 0));
            pixels5.setPixelColor(2, pixels3.Color(0, 0, 0));
            pixels5.setPixelColor(3, pixels3.Color(0, 0, 0));
            pixels5.show();
        }

        int32_t lux = analogRead(GPIO_NUM_2);
        if (luminosity.publish(lux))
        {
            Serial.println(F("Luminosity published successfully!"));
        }
        else
        {
            Serial.println(F("Failed to publish Luminosity"));
        }
        delay(12000);
    }
}

void TaskTurnOnLED(void *pvParameters)
{

    pinMode(GPIO_NUM_9, OUTPUT);
    pinMode(GPIO_NUM_8, OUTPUT);
    while (1)
    {
        if (light > 550)
        {
            digitalWrite(GPIO_NUM_9, HIGH);
            digitalWrite(GPIO_NUM_8, HIGH);
        }

        if (light < 350)
        {
            digitalWrite(GPIO_NUM_9, LOW);
            digitalWrite(GPIO_NUM_8, LOW);
        }

        vTaskDelay(5000);
    }
}

/*******************************************************************************************************/

// #include <WiFi.h>
// #include <ESPAsyncWebServer.h>
// #include <Adafruit_NeoPixel.h>
// #include <DHT20.h>
// #include <LiquidCrystal_I2C.h>
// #include <SPIFFS.h>
// #include <Wire.h>
// #include <Ultrasonic.h>

// // Access Point credentials
// #define AP_SSID "huytaideptrai"
// #define AP_PASS "123456789"

// // Pin for NeoPixel LED and Relay
// #define PIN 6
// #define NUMPIXELS 4
// #define RELAY_PIN 5  // Pin điều khiển Relay

// // Define components here
// Adafruit_NeoPixel pixels3(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);
// Adafruit_NeoPixel pixels5(4, GPIO_NUM_8, NEO_GRB + NEO_KHZ800);
// DHT20 dht20;
// LiquidCrystal_I2C lcd(33,16,2);
// Ultrasonic ultrasonic(GPIO_NUM_18, GPIO_NUM_21);

// // Create an instance of AsyncWebServer on port 80
// AsyncWebServer server(80);

// // Variable to store LED state
// bool ledState = false;
// static int moisture = 0;
// static float temperature = 0;
// static float humidity = 0;
// static int light = 0;
// static int distance = 357;

// // Task handles
// // void TaskHTTPServer(void *pvParameters);
// void TaskTemperatureHumidity(void *pvParameters);
// void TaskLEDControl(void *pvParameters);
// void TaskMoistureRelayControl(void *pvParameters);
// void TaskLightAndLED(void *pvParameters);
// void TaskDisAndFan(void *pvParameters);

// void setup() {
//   // Initialize Serial Monitor
//   Serial.begin(115200);

//   while (!SPIFFS.begin(true)) {
//     Serial.println("Failed to mount file system");
//   }

//   // Set ESP32 as an Access Point
//   WiFi.softAP(AP_SSID);  // Set the SSID and password for the Access Point
//   Serial.print("Access Point started: ");
//   Serial.println(AP_SSID);

//   // Initialize NeoPixel and DHT sensor
//   Wire.begin(GPIO_NUM_11, GPIO_NUM_12);
//   dht20.begin();
//   lcd.begin();
//   pixels3.begin();

//   // dht20.read();

//   // Set relay pin as output
//   pinMode(RELAY_PIN, OUTPUT);

//    // Create tasks
//   xTaskCreate(TaskTemperatureHumidity, "Temperature Humidity", 2048, NULL, 2, NULL);
//   xTaskCreate(TaskLEDControl, "LED Control", 2048, NULL, 2, NULL);
//   xTaskCreate(TaskMoistureRelayControl, "Moisture Relay Control", 2048, NULL, 2, NULL);
//   xTaskCreate(TaskLightAndLED, "Light and LED", 2048, NULL, 2, NULL);
//   xTaskCreate(TaskDisAndFan, "Distance and fan", 2048, NULL, 2, NULL);

//   server.on("/toggle", HTTP_GET, [](AsyncWebServerRequest *request){
//     ledState = !ledState;  // Toggle LED state
//     digitalWrite(GPIO_NUM_48, ledState ? HIGH : LOW);  // Update LED state
//     request->send(200, "text/plain", ledState ? "LED ON" : "LED OFF");
//   });

//   server.on("/getData", HTTP_GET, [](AsyncWebServerRequest *request) {
//       dht20.read();
//       distance = ultrasonic.read();
//       temperature = dht20.getTemperature();
//       humidity = dht20.getHumidity();
//       moisture = analogRead(GPIO_NUM_1);
//       light = analogRead(GPIO_NUM_2);

//       String jsonResponse = "{\"temperature\":" + String(temperature) +
//                             ",\"humidity\":" + String(humidity) +
//                             ",\"moisture\":" + String(moisture) +
//                             ",\"light\":" + String(light) +
//                             ",\"distance\":" + String(distance) + "}";

//       request->send(200, "application/json", jsonResponse);
//   });

//   // Serve the HTML file
//   server.on("/", HTTP_GET, [](AsyncWebServerRequest *request) {
//     request->send(SPIFFS, "/index2.html", "text/html");
//   });

//   // Serve the CSS file
//   server.serveStatic("/style2.css", SPIFFS, "/style2.css");
//   server.serveStatic("/scripts2.js", SPIFFS, "/scripts2.js");

//   // server the png files
//   server.serveStatic("/images/off.png", SPIFFS, "/images/off.png");
//   server.serveStatic("/images/on.png", SPIFFS, "/images/on.png");
//   server.begin();
//   Serial.println("Server started");
// }

// void loop() {
//   // Main loop doesn't need to do anything
//   // The tasks are handling everything in the background
// }

// void TaskDisAndFan(void *pvParameters)
// {
//   pinMode(GPIO_NUM_10, OUTPUT);
//   uint32_t distance = 0;
//   while(1)
//   {
//     Serial.print("Distance value: ");
//     distance = ultrasonic.read();
//     Serial.println(distance);
//     analogWrite(GPIO_NUM_10, distance > 5 ? 0 : 100);
//     vTaskDelay(500);

//   }
// }

// // Task to handle temperature and humidity readings
// void TaskTemperatureHumidity(void *pvParameters) {
//   while(1) {
//     // Read temperature and humidity from DHT sensor;
//     // dht20.read();

//     // Print to Serial Monitor
//     Serial.print("Temp: ");
//     Serial.print(temperature);
//     Serial.print(" C, Humidity: ");
//     Serial.println(humidity);

//     lcd.clear();
//     lcd.setCursor(0, 0);
//     lcd.print(temperature);
//     lcd.setCursor(0, 1);
//     lcd.print(humidity);

//     // Wait for 5 seconds before reading again
//     vTaskDelay(500);
//   }
// }

// // Task to handle LED control
// void TaskLEDControl(void *pvParameters) {
//   pinMode(GPIO_NUM_48, OUTPUT); // Initialize LED pin

//   while(1) {
//     // Serial.println("ledstate: ");
//     // Serial.println(ledState);
//     // Here you can implement additional LED control logic
//     // For example, you can blink the LED based on conditions
//     if (ledState) {
//       digitalWrite(GPIO_NUM_48, HIGH); // Turn ON LED
//     } else {
//       digitalWrite(GPIO_NUM_48, LOW); // Turn OFF LED
//     }

//   //   // Get the IP address of the Access Point
//   // IPAddress IP = WiFi.softAPIP();
//   // Serial.print("AP IP address: ");
//   // Serial.println(IP);

//     // Delay before checking again
//     vTaskDelay(1000);
//   }
// }

// // Combined Task for Moisture and Relay Control
// void TaskMoistureRelayControl(void *pvParameters) {
//   while(1) {
//     // // Read moisture level
//     Serial.print("Moisture value:");
//     Serial.println(moisture);

//     // control relay based on moisture level
//     if (moisture > 500) {
//       digitalWrite(RELAY_PIN, LOW);  // Turn OFF relay
//     } else if (moisture < 50) {
//       digitalWrite(RELAY_PIN, HIGH);  // Turn ON relay
//     }

//     if (moisture > 500){
//       digitalWrite(GPIO_NUM_6, LOW);
//     }
//     if (moisture < 50){
//      digitalWrite(GPIO_NUM_6, HIGH);
//     }

//     vTaskDelay(500);
//   }
// }

// void TaskLightAndLED(void *pvParameters) {
//     while (1){

//     Serial.print("Light value: ");
//     Serial.println(light);

//     if (light > 550){
//       pixels5.setPixelColor(0, pixels3.Color(255,0,0));
//       pixels5.setPixelColor(1, pixels3.Color(255,0,0));
//       pixels5.setPixelColor(2, pixels3.Color(255,0,0));
//       pixels5.setPixelColor(3, pixels3.Color(255,0,0));
//       pixels5.show();
//     }
//     if (light < 350){
//       pixels5.setPixelColor(0, pixels3.Color(0,0,0));
//       pixels5.setPixelColor(1, pixels3.Color(0,0,0));
//       pixels5.setPixelColor(2, pixels3.Color(0,0,0));
//       pixels5.setPixelColor(3, pixels3.Color(0,0,0));
//       pixels5.show();
//     }

//     vTaskDelay(500);
//   }
// }
