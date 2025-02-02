#include <ESP8266WiFi.h>
#include <SoftwareSerial.h>
#include <TinyGPS++.h>

// WiFi credentials
const char* ssid = "Hedgehog House";       // Replace with your WiFi SSID
const char* password = "boat2016"; // Replace with your WiFi password

// Server configuration (your computer's IP and port)
IPAddress serverIP(192, 168, 1, 96); // Replace with your computer's IP
const uint16_t serverPort = 1234;     // Replace with your desired port

// GPS Configuration
SoftwareSerial gpsSerial(D2, D3); // RX, TX (TX unused)
TinyGPSPlus gps;
WiFiClient client;

void setup() {
  Serial.begin(115200);
  Serial.println("ESP8266 booting up!");
  gpsSerial.begin(9600);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP()); // Print ESP8266's IP address
}

void loop() {
  // Maintain connection
  if (!client.connected()) {
    client.connect(serverIP, serverPort);
    delay(1000);
    return;
  }

  // Read GPS data
  while (gpsSerial.available() > 0) {
    if (gps.encode(gpsSerial.read())) {
      if (gps.location.isValid()) {
        // Send parsed data to server
        String data = 
          "Lat: " + String(gps.location.lat(), 6) + 
          ", Lng: " + String(gps.location.lng(), 6) +
          ", Sats: " + String(gps.satellites.value());
        client.println(data);
        Serial.println(data);  // Also print locally
      }
    }
  }
  

  
}