#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <DHT.h>

// =====================================================
// ADM FireNode Unified ESP32 Wiring + LoRa Test Program
// =====================================================
// Upload this same PlatformIO project to every ESP32.
// Change only NODE_ID before uploading to each board:
//   "MAIN"
//   "NODE_01"
//   "NODE_02"
//   "NODE_03"
// =====================================================

// #define NODE_ID "NODE_01"
#ifndef NODE_ID
#define NODE_ID "MAIN"
#endif


// Sensors
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define PIR_PIN 27
#define MQ_PIN 34
#define BATTERY_PIN 35
#define STATUS_LED 2

// LoRa SX1278 / RA-02 pins
#define LORA_SCK 18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_CS 5
#define LORA_RST 14
#define LORA_DIO0 26
#define LORA_FREQ 433E6

// Timing
#define SEND_INTERVAL_MS 5000

DHT dht(DHT_PIN, DHT_TYPE);

unsigned long lastSend = 0;
int packetCounter = 0;
bool loraOK = false;

void printPinoutHelp() {
  Serial.println();
  Serial.println("========== EXPECTED PINOUT ==========");
  Serial.println("DHT22 DATA      -> GPIO 4");
  Serial.println("PIR OUT         -> GPIO 27");
  Serial.println("MQ AOUT         -> GPIO 34");
  Serial.println("Battery Sense   -> GPIO 35");
  Serial.println("Status LED      -> GPIO 2");
  Serial.println("LoRa SCK        -> GPIO 18");
  Serial.println("LoRa MISO       -> GPIO 19");
  Serial.println("LoRa MOSI       -> GPIO 23");
  Serial.println("LoRa NSS/CS     -> GPIO 5");
  Serial.println("LoRa RESET      -> GPIO 14");
  Serial.println("LoRa DIO0       -> GPIO 26");
  Serial.println("LoRa VCC        -> 3.3V ONLY");
  Serial.println("LoRa GND        -> GND");
  Serial.println("=====================================");
  Serial.println();
}

void initLoRa() {
  Serial.println("[TEST] Initializing LoRa SX1278 / RA-02...");

  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_CS);
  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQ)) {
    Serial.println("[FAIL] LoRa init failed.");
    Serial.println("       Check RA-02 wiring, 3.3V power, antenna, NSS, RST, DIO0, SPI pins.");
    loraOK = false;
    return;
  }

  // Conservative LoRa defaults for bench testing.
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.enableCrc();

  Serial.println("[PASS] LoRa initialized at 433 MHz.");
  loraOK = true;
}

void sendLoRaPacket(float temp, float hum, int pir, int mqRaw, int batteryRaw) {
  if (!loraOK) {
    Serial.println("[SKIP] LoRa TX skipped because LoRa initialization failed.");
    return;
  }

  String packet = "";
  packet += "NODE=" + String(NODE_ID);
  packet += ",SEQ=" + String(packetCounter++);
  packet += ",TEMP=" + String(temp, 2);
  packet += ",HUM=" + String(hum, 2);
  packet += ",PIR=" + String(pir);
  packet += ",MQ=" + String(mqRaw);
  packet += ",BAT=" + String(batteryRaw);

  LoRa.beginPacket();
  LoRa.print(packet);
  int result = LoRa.endPacket();

  if (result == 1) {
    Serial.print("[LORA TX OK] ");
    Serial.println(packet);
  } else {
    Serial.print("[LORA TX FAIL] endPacket result: ");
    Serial.println(result);
  }
}

void receiveLoRaPacket() {
  if (!loraOK) return;

  int packetSize = LoRa.parsePacket();
  if (!packetSize) return;

  String incoming = "";
  while (LoRa.available()) {
    incoming += (char)LoRa.read();
  }

  Serial.println();
  Serial.println("========== LORA RX ==========");
  Serial.print("[RECEIVED] ");
  Serial.println(incoming);
  Serial.print("[RSSI] ");
  Serial.println(LoRa.packetRssi());
  Serial.print("[SNR] ");
  Serial.println(LoRa.packetSnr());
  Serial.println("=============================");
}

void printSensorReadingsAndTransmit() {
  digitalWrite(STATUS_LED, !digitalRead(STATUS_LED));

  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  int pirValue = digitalRead(PIR_PIN);
  int mqRaw = analogRead(MQ_PIN);
  int batteryRaw = analogRead(BATTERY_PIN);

  float mqVoltage = mqRaw * (3.3f / 4095.0f);
  float batteryAdcVoltage = batteryRaw * (3.3f / 4095.0f);

  Serial.println();
  Serial.println("---------- LOCAL SENSOR TEST ----------");
  Serial.print("NODE ID: ");
  Serial.println(NODE_ID);

  if (isnan(temp) || isnan(hum)) {
    Serial.println("[FAIL] DHT22: no valid reading. Check GPIO4, VCC, GND, and pull-up resistor.");
  } else {
    Serial.print("[PASS] DHT22: ");
    Serial.print(temp, 2);
    Serial.print(" C / ");
    Serial.print(hum, 2);
    Serial.println(" %");
  }

  Serial.print("[INFO] PIR GPIO27: ");
  Serial.println(pirValue ? "HIGH / Motion" : "LOW / No motion");

  Serial.print("[INFO] MQ GPIO34 Raw: ");
  Serial.print(mqRaw);
  Serial.print(" | ADC Voltage: ");
  Serial.print(mqVoltage, 2);
  Serial.println(" V");

  Serial.print("[INFO] Battery GPIO35 Raw: ");
  Serial.print(batteryRaw);
  Serial.print(" | ADC Voltage: ");
  Serial.print(batteryAdcVoltage, 2);
  Serial.println(" V");

  sendLoRaPacket(temp, hum, pirValue, mqRaw, batteryRaw);
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println();
  Serial.println("=========================================");
  Serial.println("ADM FireNode Unified ESP32 Test Program");
  Serial.println("=========================================");
  Serial.print("NODE ID: ");
  Serial.println(NODE_ID);

  pinMode(PIR_PIN, INPUT);
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(STATUS_LED, LOW);

  analogReadResolution(12);

  printPinoutHelp();

  Serial.println("[TEST] Starting DHT22...");
  dht.begin();

  initLoRa();

  Serial.println("[READY] Testing sensors + LoRa TX/RX every 5 seconds.");
  Serial.println("Open Serial Monitor at 115200 baud on two or more ESP32 boards.");
  Serial.println("Each board should transmit packets and receive packets from the others.");
}

void loop() {
  receiveLoRaPacket();

  if (millis() - lastSend >= SEND_INTERVAL_MS) {
    lastSend = millis();
    printSensorReadingsAndTransmit();
  }
}
