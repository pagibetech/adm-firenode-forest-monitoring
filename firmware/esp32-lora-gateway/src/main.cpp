/*
  FireNode ESP32 LoRa Gateway

  Receives SX1278/Ra-02 LoRa packets and prints one JSON object per serial line.
  The Raspberry Pi main server ingests those lines with lora_gateway_serial.py.
*/

#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>

#define LORA_SCK 18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_SS 5
#define LORA_RST 14
#define LORA_DIO0 26

const long LORA_FREQUENCY = 433E6;
const int LORA_SPREADING_FACTOR = 7;
const long LORA_SIGNAL_BANDWIDTH = 125E3;
const int LORA_CODING_RATE_DENOMINATOR = 5;
const byte LORA_SYNC_WORD = 0x12;

uint32_t gatewaySeq = 0;
bool loraReady = false;

String jsonEscape(const String &input) {
  String out;
  out.reserve(input.length() + 8);
  for (size_t i = 0; i < input.length(); i++) {
    char c = input.charAt(i);
    if (c == '\\' || c == '"') {
      out += '\\';
      out += c;
    } else if (c == '\n') {
      out += "\\n";
    } else if (c == '\r') {
      out += "\\r";
    } else if (c == '\t') {
      out += "\\t";
    } else if ((uint8_t)c < 0x20) {
      out += ' ';
    } else {
      out += c;
    }
  }
  return out;
}

String extractJsonValue(const String &json, const String &key) {
  String needle = "\"" + key + "\"";
  int keyPos = json.indexOf(needle);
  if (keyPos < 0) return "";
  int colon = json.indexOf(':', keyPos + needle.length());
  if (colon < 0) return "";
  int pos = colon + 1;
  while (pos < (int)json.length() && isspace(json.charAt(pos))) pos++;
  if (pos >= (int)json.length()) return "";

  if (json.charAt(pos) == '"') {
    int end = pos + 1;
    bool escaped = false;
    while (end < (int)json.length()) {
      char c = json.charAt(end);
      if (c == '"' && !escaped) break;
      escaped = (c == '\\' && !escaped);
      if (c != '\\') escaped = false;
      end++;
    }
    return json.substring(pos + 1, end);
  }

  int end = pos;
  while (end < (int)json.length()) {
    char c = json.charAt(end);
    if (c == ',' || c == '}') break;
    end++;
  }
  String value = json.substring(pos, end);
  value.trim();
  return value;
}

uint32_t extractSeq(const String &payload) {
  String seqText = extractJsonValue(payload, "seq");
  if (seqText.length() == 0) {
    seqText = extractJsonValue(payload, "uptime");
  }
  if (seqText.length() == 0) {
    gatewaySeq++;
    return gatewaySeq;
  }
  return (uint32_t)seqText.toInt();
}

int extractSlotFromNodeId(const String &nodeId) {
  if (nodeId.length() == 0) return 0;
  for (int i = nodeId.length() - 1; i >= 0; i--) {
    if (!isDigit(nodeId.charAt(i))) {
      if (i == (int)nodeId.length() - 1) return 0;
      return nodeId.substring(i + 1).toInt();
    }
  }
  return nodeId.toInt();
}

String normalizedPayloadJson(const String &rawPayload) {
  String nodeId = extractJsonValue(rawPayload, "node_id");
  String temp = extractJsonValue(rawPayload, "temperature");
  String humidity = extractJsonValue(rawPayload, "humidity");
  String smoke = extractJsonValue(rawPayload, "smoke_ppm");
  if (smoke.length() == 0) smoke = extractJsonValue(rawPayload, "smoke");
  String smokeDetected = extractJsonValue(rawPayload, "smoke_detected");
  String pirHuman = extractJsonValue(rawPayload, "human_detected");
  String battery = extractJsonValue(rawPayload, "battery_v");

  String out;
  out.reserve(rawPayload.length() + 120);
  out += "{";
  out += "\"node_id\":\"" + jsonEscape(nodeId) + "\",";
  out += "\"temperature_c\":" + (temp.length() ? temp : "null") + ",";
  out += "\"humidity_pct\":" + (humidity.length() ? humidity : "null") + ",";
  out += "\"smoke_ppm\":" + (smoke.length() ? smoke : "null") + ",";
  out += "\"smoke_detected\":" + (smokeDetected.length() ? smokeDetected : "false") + ",";
  out += "\"pir_human\":" + (pirHuman.length() ? pirHuman : "false") + ",";
  out += "\"battery_v\":" + (battery.length() ? battery : "null") + ",";
  out += "\"raw_sender_packet\":\"" + jsonEscape(rawPayload) + "\"";
  out += "}";
  return out;
}

String buildGatewayPacket(const String &payload, int rssi, float snr) {
  String nodeId = extractJsonValue(payload, "node_id");
  if (nodeId.length() == 0) nodeId = "UNKNOWN";
  uint32_t seq = extractSeq(payload);
  int slot = extractSlotFromNodeId(nodeId);
  String packetId = "GW-" + nodeId + "-" + String(seq);

  String out;
  out.reserve(payload.length() + 420);
  out += "{";
  out += "\"packet_id\":\"" + jsonEscape(packetId) + "\",";
  out += "\"timestamp\":\"" + String(millis()) + "\",";
  out += "\"node_id\":\"" + jsonEscape(nodeId) + "\",";
  out += "\"node_name\":\"" + jsonEscape(nodeId) + "\",";
  out += "\"slot\":" + String(slot) + ",";
  out += "\"seq\":" + String(seq) + ",";
  out += "\"rssi_dbm\":" + String(rssi) + ",";
  out += "\"snr_db\":" + String(snr, 2) + ",";
  out += "\"frequency_mhz\":433.00,";
  out += "\"spreading_factor\":" + String(LORA_SPREADING_FACTOR) + ",";
  out += "\"bandwidth_khz\":125.0,";
  out += "\"received\":true,";
  out += "\"payload\":" + normalizedPayloadJson(payload);
  out += "}";
  return out;
}

bool initLoRa() {
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("{\"gateway_status\":\"lora_init_failed\"}");
    return false;
  }

  LoRa.setSpreadingFactor(LORA_SPREADING_FACTOR);
  LoRa.setSignalBandwidth(LORA_SIGNAL_BANDWIDTH);
  LoRa.setCodingRate4(LORA_CODING_RATE_DENOMINATOR);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.enableCrc();
  Serial.println("{\"gateway_status\":\"ready\",\"frequency_mhz\":433.00}");
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  loraReady = initLoRa();
}

void loop() {
  if (!loraReady) {
    delay(2000);
    loraReady = initLoRa();
    return;
  }

  int packetSize = LoRa.parsePacket();
  if (!packetSize) {
    delay(10);
    return;
  }

  String payload;
  payload.reserve(packetSize + 8);
  while (LoRa.available()) {
    payload += (char)LoRa.read();
  }
  payload.trim();
  if (payload.length() == 0) {
    return;
  }

  Serial.println(buildGatewayPacket(payload, LoRa.packetRssi(), LoRa.packetSnr()));
}
