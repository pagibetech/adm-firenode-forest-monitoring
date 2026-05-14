/*
  FireNode ESP32 LoRa Sensor Sender

  Hardware:
  - ESP32 WROOM-32
  - DHT22 temperature/humidity sensor
  - MQ2 smoke sensor digital output only
  - PIR motion sensor for human/motion detection
  - SX1278 / Ra-02 LoRa module, 433 MHz

  Features:
  - Open AP SSID: FireNode
  - AP + STA enabled at the same time
  - Wi-Fi scan/connect web GUI
  - Saved Wi-Fi credentials using ESP32 Preferences/NVS
  - /data JSON endpoint
  - LoRa JSON packet sender
  - Editable send interval, default 3 seconds
  - Simulation mode for development without sensors
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include <SPI.h>
#include <LoRa.h>
#include <DHT.h>
#include <math.h>

// =========================
// Pin assignments
// =========================
#define DHT_PIN 27
#define DHT_TYPE DHT22
#define MQ2_DIGITAL_PIN 34
#define PIR_PIN 32

#define LORA_SCK 18
#define LORA_MISO 19
#define LORA_MOSI 23
#define LORA_SS 5
#define LORA_RST 14
#define LORA_DIO0 26

// =========================
// System defaults
// =========================
const char *AP_SSID = "FireNode";
const uint32_t DEFAULT_SEND_INTERVAL_SEC = 3;
const uint32_t MIN_SEND_INTERVAL_SEC = 1;
const uint32_t MAX_SEND_INTERVAL_SEC = 3600;
const uint32_t WIFI_RECONNECT_INTERVAL_MS = 10000;
const uint32_t SENSOR_READ_INTERVAL_MS = 2000;

// Most LM393-based MQ2 modules output LOW when smoke/gas exceeds the trimpot threshold.
// If your module outputs HIGH when smoke is detected, change this to false.
const bool MQ2_ACTIVE_LOW = true;

// Most PIR modules output HIGH when motion is detected.
// If your PIR module outputs LOW when motion is detected, change this to false.
const bool PIR_ACTIVE_HIGH = true;

// LoRa defaults
const long LORA_FREQUENCY = 433E6;
const int LORA_SPREADING_FACTOR = 7;
const long LORA_SIGNAL_BANDWIDTH = 125E3;
const int LORA_CODING_RATE_DENOMINATOR = 5;
const byte LORA_SYNC_WORD = 0x12;
const int LORA_TX_POWER_DBM = 17;

// =========================
// Global objects
// =========================
WebServer server(80);
Preferences prefs;
DHT dht(DHT_PIN, DHT_TYPE);

// =========================
// Runtime state
// =========================
String savedSsid = "";
String savedPassword = "";

bool simulationMode = true;
uint32_t sendIntervalSec = DEFAULT_SEND_INTERVAL_SEC;

bool loraReady = false;
bool lastLoraSendOk = false;
String lastLoraPacket = "";
uint32_t loraSendCount = 0;
uint32_t loraFailCount = 0;
unsigned long lastLoraSendMs = 0;

float temperatureC = NAN;
float humidityPct = NAN;
int smokeRaw = HIGH;
bool smokeDetected = false;
int pirRaw = LOW;
bool humanDetected = false;
bool dhtValid = false;

unsigned long lastSensorReadMs = 0;
unsigned long lastWifiReconnectAttemptMs = 0;

// =========================
// Web GUI HTML
// =========================
const char INDEX_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FireNode ESP32</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --card: #1f2937;
      --muted: #94a3b8;
      --text: #f8fafc;
      --line: #334155;
      --ok: #22c55e;
      --warn: #f59e0b;
      --bad: #ef4444;
      --blue: #38bdf8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: radial-gradient(circle at top, #1e293b 0, var(--bg) 45%, #020617 100%);
      color: var(--text);
    }
    header {
      padding: 18px 16px;
      border-bottom: 1px solid var(--line);
      background: rgba(15, 23, 42, 0.9);
      position: sticky;
      top: 0;
      z-index: 5;
      backdrop-filter: blur(8px);
    }
    h1 { margin: 0; font-size: 1.4rem; }
    .subtitle { color: var(--muted); font-size: 0.9rem; margin-top: 4px; }
    main { padding: 16px; max-width: 1150px; margin: 0 auto; }
    .grid { display: grid; grid-template-columns: repeat(12, 1fr); gap: 14px; align-items: start; }
    .card {
      grid-column: span 4;
      background: rgba(31, 41, 55, 0.88);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 16px 40px rgba(0,0,0,0.25);
    }
    .wide { grid-column: span 8; }
    .full { grid-column: span 12; }
    .stack { grid-column: span 4; display: flex; flex-direction: column; gap: 14px; }
    .stack .card { grid-column: auto; width: 100%; }
    .compact-card { padding: 14px 16px; }
    .label { color: var(--muted); font-size: 0.84rem; margin-bottom: 6px; }
    .value { font-size: 1.6rem; font-weight: bold; word-break: break-word; }
    .small-value { font-size: 1rem; font-weight: bold; word-break: break-word; }
    .pill {
      display: inline-block;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: bold;
      margin-top: 6px;
    }
    .ok { background: rgba(34,197,94,0.16); color: var(--ok); border: 1px solid rgba(34,197,94,0.35); }
    .warn { background: rgba(245,158,11,0.16); color: var(--warn); border: 1px solid rgba(245,158,11,0.35); }
    .bad { background: rgba(239,68,68,0.16); color: var(--bad); border: 1px solid rgba(239,68,68,0.35); }
    .blue { background: rgba(56,189,248,0.16); color: var(--blue); border: 1px solid rgba(56,189,248,0.35); }
    button, input, select {
      width: 100%;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--line);
      font-size: 1rem;
    }
    input, select {
      background: #020617;
      color: var(--text);
      margin: 5px 0 12px 0;
    }
    button {
      cursor: pointer;
      background: #2563eb;
      color: white;
      border: none;
      font-weight: bold;
      margin-top: 6px;
    }
    button.secondary { background: #475569; }
    button.danger { background: #dc2626; }
    button.success { background: #16a34a; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .row { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .status-line { color: var(--muted); margin-top: 10px; font-size: 0.9rem; min-height: 20px; }
    pre {
      background: #020617;
      color: #d1d5db;
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 12px;
      overflow: auto;
      max-height: 300px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .checkbox-row {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 8px 0 12px 0;
    }
    .checkbox-row input { width: auto; margin: 0; }
    .footer-note { color: var(--muted); font-size: 0.82rem; margin-top: 12px; line-height: 1.35; }
    @media (max-width: 900px) {
      .card, .wide, .stack { grid-column: span 12; }
      .row { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
<header>
  <h1>FireNode ESP32 Sensor + LoRa Sender</h1>
  <div class="subtitle">AP SSID: FireNode | AP + STA enabled | JSON endpoint: /data</div>
</header>
<main>
  <div class="grid">
    <section class="card full">
      <div class="label">Node ID</div>
      <div class="value" id="node_id">--</div>
      <span class="pill blue" id="uptime">Uptime: --</span>
      <span class="pill" id="sim_pill">Simulation: --</span>
    </section>

    <section class="card">
      <div class="label">Temperature</div>
      <div class="value" id="temperature">-- °C</div>
      <span class="pill" id="dht_status">DHT22: --</span>
    </section>

    <section class="card">
      <div class="label">Humidity</div>
      <div class="value" id="humidity">-- %</div>
      <span class="pill blue">DHT22</span>
    </section>

    <section class="card">
      <div class="label">MQ2 Smoke Digital Status</div>
      <div class="value" id="smoke">--</div>
      <span class="pill" id="smoke_pill">Raw: --</span>
    </section>

    <section class="card">
      <div class="label">PIR Human Detection</div>
      <div class="value" id="human">--</div>
      <span class="pill" id="pir_pill">Raw: --</span>
    </section>

    <section class="card">
      <div class="label">STA Wi-Fi</div>
      <div class="small-value" id="sta_status">--</div>
      <div class="footer-note" id="sta_details">--</div>
    </section>

    <section class="card">
      <div class="label">AP Wi-Fi</div>
      <div class="small-value" id="ap_ip">--</div>
      <div class="footer-note">Connect to open SSID <b>FireNode</b> for setup.</div>
    </section>

    <div class="stack">
      <section class="card compact-card">
        <div class="label">LoRa Status</div>
        <div class="small-value" id="lora_status">--</div>
        <div class="footer-note" id="lora_details">--</div>
        <button class="success" onclick="sendTestLoRa()">Send Test LoRa Packet Now</button>
      </section>

      <section class="card">
        <h2>Node Settings</h2>
        <label class="label" for="interval">LoRa Send Interval, seconds</label>
        <input id="interval" type="number" min="1" max="3600" value="3">
        <div class="checkbox-row">
          <input id="simulation" type="checkbox">
          <label for="simulation">Simulation mode</label>
        </div>
        <button onclick="saveSettings()">Save Settings</button>
        <div class="status-line" id="settings_msg"></div>
      </section>
    </div>

    <section class="card wide">
      <h2>Wi-Fi Setup</h2>
      <button onclick="scanWifi()">Scan Wi-Fi</button>
      <div class="status-line" id="scan_status"></div>
      <label class="label" for="ssid_select">Available 2.4 GHz Networks</label>
      <select id="ssid_select" onchange="copySelectedSsid()">
        <option value="">Press Scan Wi-Fi</option>
      </select>
      <label class="label" for="ssid">SSID</label>
      <input id="ssid" placeholder="Wi-Fi SSID">
      <label class="label" for="password">Password</label>
      <input id="password" type="password" placeholder="Wi-Fi password">
      <div class="row">
        <button onclick="saveWifi()">Save & Connect</button>
        <button class="danger" onclick="forgetWifi()">Forget Saved Wi-Fi</button>
      </div>
      <div class="status-line" id="wifi_msg"></div>
    </section>

    <section class="card full">
      <h2>/data JSON</h2>
      <pre id="json_box">Loading...</pre>
    </section>

    <section class="card full">
      <h2>Last LoRa JSON Packet</h2>
      <pre id="packet_box">No packet sent yet.</pre>
    </section>
  </div>
</main>
<script>
let firstLoad = true;

function setPill(el, cls, text) {
  el.className = 'pill ' + cls;
  el.textContent = text;
}

function fmtNum(v, digits) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '--';
  return Number(v).toFixed(digits);
}

async function refreshData() {
  try {
    const res = await fetch('/data', { cache: 'no-store' });
    const data = await res.json();

    document.getElementById('json_box').textContent = JSON.stringify(data, null, 2);
    document.getElementById('node_id').textContent = data.node_id || '--';
    document.getElementById('uptime').textContent = 'Uptime: ' + data.uptime + ' s';

    document.getElementById('temperature').textContent = fmtNum(data.temperature, 1) + ' °C';
    document.getElementById('humidity').textContent = fmtNum(data.humidity, 1) + ' %';

    if (data.simulation) {
      setPill(document.getElementById('sim_pill'), 'warn', 'Simulation: ON');
    } else {
      setPill(document.getElementById('sim_pill'), 'ok', 'Simulation: OFF');
    }

    if (data.dht_valid || data.simulation) {
      setPill(document.getElementById('dht_status'), 'ok', 'DHT22: OK');
    } else {
      setPill(document.getElementById('dht_status'), 'bad', 'DHT22: No valid reading');
    }

    document.getElementById('smoke').textContent = data.smoke_detected ? 'SMOKE DETECTED' : 'No Smoke';
    setPill(document.getElementById('smoke_pill'), data.smoke_detected ? 'bad' : 'ok', 'Raw: ' + data.smoke);

    document.getElementById('human').textContent = data.human_detected ? 'HUMAN / MOTION DETECTED' : 'No Human Motion';
    setPill(document.getElementById('pir_pill'), data.human_detected ? 'bad' : 'ok', 'Raw: ' + data.pir);

    document.getElementById('sta_status').textContent = data.sta_connected ? 'Connected to ' + data.wifi_ssid : 'Not connected';
    document.getElementById('sta_details').innerHTML = 'STA IP: <b>' + data.sta_ip + '</b><br>RSSI: ' + data.rssi + ' dBm';
    document.getElementById('ap_ip').textContent = 'AP IP: ' + data.ap_ip;

    document.getElementById('lora_status').textContent = data.lora_ready ? 'LoRa Ready' : 'LoRa Not Ready';
    document.getElementById('lora_details').innerHTML =
      'Last send: ' + (data.last_lora_send_ok ? 'OK' : 'Failed/None') +
      '<br>Sent: ' + data.lora_send_count +
      '<br>Failed: ' + data.lora_fail_count +
      '<br>Interval: ' + data.send_interval_s + ' s';

    document.getElementById('packet_box').textContent = data.last_lora_packet || 'No packet sent yet.';

    if (firstLoad) {
      document.getElementById('interval').value = data.send_interval_s;
      document.getElementById('simulation').checked = !!data.simulation;
      firstLoad = false;
    }
  } catch (err) {
    document.getElementById('json_box').textContent = 'Failed to fetch /data: ' + err;
  }
}

async function scanWifi() {
  const status = document.getElementById('scan_status');
  const select = document.getElementById('ssid_select');
  status.textContent = 'Scanning...';
  select.innerHTML = '<option value="">Scanning...</option>';
  try {
    const res = await fetch('/scan', { cache: 'no-store' });
    const networks = await res.json();
    select.innerHTML = '';
    if (!networks.length) {
      select.innerHTML = '<option value="">No networks found</option>';
      status.textContent = 'No networks found.';
      return;
    }
    networks.forEach(n => {
      const opt = document.createElement('option');
      opt.value = n.ssid;
      opt.textContent = n.ssid + ' | RSSI ' + n.rssi + ' dBm | ' + (n.encryption ? 'Secured' : 'Open');
      select.appendChild(opt);
    });
    copySelectedSsid();
    status.textContent = 'Scan complete. Found ' + networks.length + ' network(s).';
  } catch (err) {
    status.textContent = 'Scan failed: ' + err;
  }
}

function copySelectedSsid() {
  const select = document.getElementById('ssid_select');
  if (select.value) document.getElementById('ssid').value = select.value;
}

async function saveWifi() {
  const msg = document.getElementById('wifi_msg');
  const form = new URLSearchParams();
  form.append('ssid', document.getElementById('ssid').value);
  form.append('password', document.getElementById('password').value);
  msg.textContent = 'Saving Wi-Fi settings...';
  try {
    const res = await fetch('/wifi', { method: 'POST', body: form });
    msg.textContent = await res.text();
    setTimeout(refreshData, 2000);
  } catch (err) {
    msg.textContent = 'Failed: ' + err;
  }
}

async function forgetWifi() {
  const msg = document.getElementById('wifi_msg');
  msg.textContent = 'Clearing saved Wi-Fi...';
  try {
    const res = await fetch('/forget-wifi', { method: 'POST' });
    msg.textContent = await res.text();
    setTimeout(refreshData, 1000);
  } catch (err) {
    msg.textContent = 'Failed: ' + err;
  }
}

async function saveSettings() {
  const msg = document.getElementById('settings_msg');
  const form = new URLSearchParams();
  form.append('interval', document.getElementById('interval').value);
  form.append('simulation', document.getElementById('simulation').checked ? '1' : '0');
  msg.textContent = 'Saving settings...';
  try {
    const res = await fetch('/settings', { method: 'POST', body: form });
    msg.textContent = await res.text();
    firstLoad = true;
    setTimeout(refreshData, 500);
  } catch (err) {
    msg.textContent = 'Failed: ' + err;
  }
}

async function sendTestLoRa() {
  try {
    const res = await fetch('/send-test', { method: 'POST' });
    alert(await res.text());
    setTimeout(refreshData, 500);
  } catch (err) {
    alert('Failed: ' + err);
  }
}

refreshData();
setInterval(refreshData, 2000);
</script>
</body>
</html>
)HTML";

// =========================
// Utility functions
// =========================
String ipToString(IPAddress ip) {
  return String(ip[0]) + "." + String(ip[1]) + "." + String(ip[2]) + "." + String(ip[3]);
}

String jsonEscape(const String &input) {
  String out;
  out.reserve(input.length() + 8);
  for (size_t i = 0; i < input.length(); i++) {
    char c = input.charAt(i);
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if ((uint8_t)c < 0x20) {
          out += " ";
        } else {
          out += c;
        }
        break;
    }
  }
  return out;
}

String boolJson(bool value) {
  return value ? "true" : "false";
}

String getStaIpString() {
  if (WiFi.status() == WL_CONNECTED) return ipToString(WiFi.localIP());
  return "0.0.0.0";
}

String getApIpString() {
  return ipToString(WiFi.softAPIP());
}

String getNodeId() {
  String ip = (WiFi.status() == WL_CONNECTED) ? getStaIpString() : getApIpString();
  ip.replace('.', '-');
  return String("FireNode-") + ip;
}

String formatFloatForJson(float value, uint8_t digits) {
  if (isnan(value) || isinf(value)) return "null";
  return String((double)value, (unsigned int)digits);
}

// =========================
// Preferences
// =========================
void loadPreferences() {
  prefs.begin("firenode", false);
  savedSsid = prefs.getString("ssid", "");
  savedPassword = prefs.getString("pass", "");
  sendIntervalSec = prefs.getUInt("interval", DEFAULT_SEND_INTERVAL_SEC);
  simulationMode = prefs.getBool("sim", true);

  if (sendIntervalSec < MIN_SEND_INTERVAL_SEC || sendIntervalSec > MAX_SEND_INTERVAL_SEC) {
    sendIntervalSec = DEFAULT_SEND_INTERVAL_SEC;
  }
}

void saveWifiCredentials(const String &ssid, const String &password) {
  savedSsid = ssid;
  savedPassword = password;
  prefs.putString("ssid", savedSsid);
  prefs.putString("pass", savedPassword);
}

void clearWifiCredentials() {
  savedSsid = "";
  savedPassword = "";
  prefs.remove("ssid");
  prefs.remove("pass");
}

void saveNodeSettings() {
  prefs.putUInt("interval", sendIntervalSec);
  prefs.putBool("sim", simulationMode);
}

// =========================
// Sensor handling
// =========================
void readSensors() {
  if (simulationMode) {
    float t = millis() / 1000.0f;
    temperatureC = 30.0f + 3.0f * sin(t / 12.0f);
    humidityPct = 70.0f + 10.0f * sin(t / 17.0f);
    smokeDetected = ((millis() / 30000UL) % 2UL) == 1UL;
    smokeRaw = smokeDetected ? (MQ2_ACTIVE_LOW ? LOW : HIGH) : (MQ2_ACTIVE_LOW ? HIGH : LOW);
    humanDetected = ((millis() / 45000UL) % 2UL) == 1UL;
    pirRaw = humanDetected ? (PIR_ACTIVE_HIGH ? HIGH : LOW) : (PIR_ACTIVE_HIGH ? LOW : HIGH);
    dhtValid = true;
    return;
  }

  float newHumidity = dht.readHumidity();
  float newTemperature = dht.readTemperature();

  if (!isnan(newHumidity) && !isnan(newTemperature)) {
    humidityPct = newHumidity;
    temperatureC = newTemperature;
    dhtValid = true;
  } else {
    dhtValid = false;
  }

  smokeRaw = digitalRead(MQ2_DIGITAL_PIN);
  smokeDetected = MQ2_ACTIVE_LOW ? (smokeRaw == LOW) : (smokeRaw == HIGH);

  pirRaw = digitalRead(PIR_PIN);
  humanDetected = PIR_ACTIVE_HIGH ? (pirRaw == HIGH) : (pirRaw == LOW);
}

void readSensorsIfNeeded() {
  if (millis() - lastSensorReadMs >= SENSOR_READ_INTERVAL_MS || lastSensorReadMs == 0) {
    lastSensorReadMs = millis();
    readSensors();
  }
}

// =========================
// LoRa handling
// =========================
bool initLoRa() {
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(LORA_FREQUENCY)) {
    Serial.println("[LoRa] Failed to initialize SX1278/Ra-02.");
    return false;
  }

  LoRa.setSpreadingFactor(LORA_SPREADING_FACTOR);
  LoRa.setSignalBandwidth(LORA_SIGNAL_BANDWIDTH);
  LoRa.setCodingRate4(LORA_CODING_RATE_DENOMINATOR);
  LoRa.setSyncWord(LORA_SYNC_WORD);
  LoRa.setTxPower(LORA_TX_POWER_DBM);
  LoRa.enableCrc();

  Serial.println("[LoRa] Initialized successfully at 433 MHz.");
  return true;
}

String buildLoRaJsonPacket() {
  String packet;
  packet.reserve(300);

  packet += "{";
  packet += "\"node_id\":\"" + jsonEscape(getNodeId()) + "\",";
  packet += "\"sta_ip\":\"" + jsonEscape(getStaIpString()) + "\",";
  packet += "\"ap_ip\":\"" + jsonEscape(getApIpString()) + "\",";
  packet += "\"temperature\":" + formatFloatForJson(temperatureC, 1) + ",";
  packet += "\"humidity\":" + formatFloatForJson(humidityPct, 1) + ",";
  packet += "\"smoke\":" + String(smokeRaw) + ",";
  packet += "\"smoke_detected\":" + boolJson(smokeDetected) + ",";
  packet += "\"pir\":" + String(pirRaw) + ",";
  packet += "\"human_detected\":" + boolJson(humanDetected) + ",";
  packet += "\"simulation\":" + boolJson(simulationMode) + ",";
  packet += "\"uptime\":" + String(millis() / 1000UL);
  packet += "}";

  return packet;
}

bool sendLoRaPacket() {
  readSensorsIfNeeded();
  lastLoraPacket = buildLoRaJsonPacket();

  // IMPORTANT:
  // Update this timestamp before checking loraReady.
  // If the LoRa module is missing or wired incorrectly, loraReady stays false.
  // Without this line, the loop retries thousands of times per second,
  // causing huge fail counts, Serial spam, slow web response, and delayed Wi-Fi access.
  lastLoraSendMs = millis();

  if (!loraReady) {
    loraFailCount++;
    lastLoraSendOk = false;
    Serial.println("[LoRa] Not ready. Packet not sent. Will retry on next interval.");
    return false;
  }

  Serial.print("[LoRa] Sending: ");
  Serial.println(lastLoraPacket);

  int beginOk = LoRa.beginPacket();
  if (beginOk == 0) {
    loraFailCount++;
    lastLoraSendOk = false;
    Serial.println("[LoRa] beginPacket failed.");
    return false;
  }

  LoRa.print(lastLoraPacket);
  int endOk = LoRa.endPacket();

  if (endOk == 1) {
    loraSendCount++;
    lastLoraSendOk = true;
    Serial.println("[LoRa] Sent OK.");
    return true;
  }

  loraFailCount++;
  lastLoraSendOk = false;
  Serial.println("[LoRa] endPacket failed.");
  return false;
}

void sendLoRaIfNeeded() {
  uint32_t intervalMs = sendIntervalSec * 1000UL;
  if (millis() - lastLoraSendMs >= intervalMs || lastLoraSendMs == 0) {
    sendLoRaPacket();
  }
}

// =========================
// Wi-Fi handling
// =========================
void startAccessPoint() {
  bool apOk = WiFi.softAP(AP_SSID);
  Serial.print("[WiFi] AP SSID: ");
  Serial.println(AP_SSID);
  Serial.print("[WiFi] AP status: ");
  Serial.println(apOk ? "OK" : "FAILED");
  Serial.print("[WiFi] AP IP: ");
  Serial.println(WiFi.softAPIP());
}

void connectToSavedWifi() {
  if (savedSsid.length() == 0) {
    Serial.println("[WiFi] No saved STA credentials.");
    return;
  }

  Serial.print("[WiFi] Connecting to saved SSID: ");
  Serial.println(savedSsid);
  WiFi.begin(savedSsid.c_str(), savedPassword.c_str());
  lastWifiReconnectAttemptMs = millis();
}

void startWifi() {
  // Keep Wi-Fi responsive for LAN access.
  // persistent(false) avoids repeated flash writes when reconnecting.
  // setSleep(false) reduces delayed responses when accessed through the STA IP.
  WiFi.persistent(false);
  WiFi.mode(WIFI_AP_STA);
  WiFi.setAutoReconnect(true);
  WiFi.setSleep(false);
  delay(100);
  startAccessPoint();
  connectToSavedWifi();
}

void maintainWifiConnection() {
  if (savedSsid.length() == 0) return;
  if (WiFi.status() == WL_CONNECTED) return;

  if (millis() - lastWifiReconnectAttemptMs >= WIFI_RECONNECT_INTERVAL_MS) {
    Serial.print("[WiFi] Reconnecting to ");
    Serial.println(savedSsid);
    WiFi.disconnect(false, false);
    WiFi.begin(savedSsid.c_str(), savedPassword.c_str());
    lastWifiReconnectAttemptMs = millis();
  }
}

// =========================
// HTTP response builders
// =========================
String buildDataJson() {
  readSensorsIfNeeded();

  bool staConnected = WiFi.status() == WL_CONNECTED;

  String json;
  json.reserve(900 + lastLoraPacket.length());
  json += "{";
  json += "\"node_id\":\"" + jsonEscape(getNodeId()) + "\",";
  json += "\"ap_ssid\":\"" + String(AP_SSID) + "\",";
  json += "\"ap_ip\":\"" + jsonEscape(getApIpString()) + "\",";
  json += "\"sta_connected\":" + boolJson(staConnected) + ",";
  json += "\"sta_ip\":\"" + jsonEscape(getStaIpString()) + "\",";
  json += "\"wifi_ssid\":\"" + jsonEscape(staConnected ? WiFi.SSID() : savedSsid) + "\",";
  json += "\"rssi\":" + String(staConnected ? WiFi.RSSI() : 0) + ",";
  json += "\"temperature\":" + formatFloatForJson(temperatureC, 1) + ",";
  json += "\"humidity\":" + formatFloatForJson(humidityPct, 1) + ",";
  json += "\"smoke\":" + String(smokeRaw) + ",";
  json += "\"smoke_detected\":" + boolJson(smokeDetected) + ",";
  json += "\"pir\":" + String(pirRaw) + ",";
  json += "\"human_detected\":" + boolJson(humanDetected) + ",";
  json += "\"dht_valid\":" + boolJson(dhtValid) + ",";
  json += "\"simulation\":" + boolJson(simulationMode) + ",";
  json += "\"send_interval_s\":" + String(sendIntervalSec) + ",";
  json += "\"lora_ready\":" + boolJson(loraReady) + ",";
  json += "\"last_lora_send_ok\":" + boolJson(lastLoraSendOk) + ",";
  json += "\"lora_send_count\":" + String(loraSendCount) + ",";
  json += "\"lora_fail_count\":" + String(loraFailCount) + ",";
  json += "\"last_lora_send_ms\":" + String(lastLoraSendMs) + ",";
  json += "\"last_lora_packet\":\"" + jsonEscape(lastLoraPacket) + "\",";
  json += "\"uptime\":" + String(millis() / 1000UL);
  json += "}";
  return json;
}

String buildWifiScanJson() {
  int n = WiFi.scanNetworks(false, true);
  String json = "[";

  for (int i = 0; i < n; i++) {
    if (i > 0) json += ",";
    json += "{";
    json += "\"ssid\":\"" + jsonEscape(WiFi.SSID(i)) + "\",";
    json += "\"rssi\":" + String(WiFi.RSSI(i)) + ",";
    json += "\"encryption\":" + boolJson(WiFi.encryptionType(i) != WIFI_AUTH_OPEN);
    json += "}";
  }

  json += "]";
  WiFi.scanDelete();
  return json;
}

// =========================
// Web routes
// =========================
void handleRoot() {
  server.send_P(200, "text/html", INDEX_HTML);
}

void handleData() {
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", buildDataJson());
}

void handleHealth() {
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "text/plain", "OK " + getNodeId() + " uptime=" + String(millis() / 1000UL) + "s");
}

void handleScan() {
  server.sendHeader("Cache-Control", "no-store");
  server.send(200, "application/json", buildWifiScanJson());
}

void handleWifiSave() {
  if (!server.hasArg("ssid")) {
    server.send(400, "text/plain", "Missing SSID.");
    return;
  }

  String ssid = server.arg("ssid");
  String password = server.arg("password");
  ssid.trim();

  if (ssid.length() == 0) {
    server.send(400, "text/plain", "SSID cannot be empty.");
    return;
  }

  saveWifiCredentials(ssid, password);

  WiFi.disconnect(false, false);
  delay(100);
  WiFi.begin(savedSsid.c_str(), savedPassword.c_str());
  lastWifiReconnectAttemptMs = millis();

  String msg = "Saved Wi-Fi credentials. Connecting to " + savedSsid + ". Refresh /data after a few seconds to check STA IP.";
  server.send(200, "text/plain", msg);
}

void handleForgetWifi() {
  clearWifiCredentials();
  WiFi.disconnect(false, true);
  delay(100);
  server.send(200, "text/plain", "Saved Wi-Fi credentials cleared. AP FireNode remains active.");
}

void handleSettings() {
  if (server.hasArg("interval")) {
    uint32_t requested = (uint32_t) server.arg("interval").toInt();
    if (requested < MIN_SEND_INTERVAL_SEC) requested = MIN_SEND_INTERVAL_SEC;
    if (requested > MAX_SEND_INTERVAL_SEC) requested = MAX_SEND_INTERVAL_SEC;
    sendIntervalSec = requested;
  }

  if (server.hasArg("simulation")) {
    String sim = server.arg("simulation");
    simulationMode = (sim == "1" || sim == "true" || sim == "on");
  }

  saveNodeSettings();
  readSensors();

  server.send(200, "text/plain", "Settings saved. Interval: " + String(sendIntervalSec) + " s, Simulation: " + String(simulationMode ? "ON" : "OFF"));
}

void handleSendTest() {
  bool ok = sendLoRaPacket();
  if (ok) {
    server.send(200, "text/plain", "Test LoRa packet sent successfully.");
  } else {
    server.send(500, "text/plain", "Failed to send test LoRa packet. Check SX1278 wiring and power.");
  }
}

void handleNotFound() {
  server.send(404, "text/plain", "Not found. Available endpoints: /, /data, /health, /scan");
}

void startWebServer() {
  server.on("/", HTTP_GET, handleRoot);
  server.on("/data", HTTP_GET, handleData);
  server.on("/health", HTTP_GET, handleHealth);
  server.on("/scan", HTTP_GET, handleScan);
  server.on("/wifi", HTTP_POST, handleWifiSave);
  server.on("/forget-wifi", HTTP_POST, handleForgetWifi);
  server.on("/settings", HTTP_POST, handleSettings);
  server.on("/send-test", HTTP_POST, handleSendTest);
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.println("[HTTP] Web server started on port 80.");
}

// =========================
// Arduino setup/loop
// =========================
void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("====================================");
  Serial.println("FireNode ESP32 LoRa Sensor Sender");
  Serial.println("====================================");

  pinMode(MQ2_DIGITAL_PIN, INPUT);
  pinMode(PIR_PIN, INPUT_PULLDOWN);
  dht.begin();

  loadPreferences();
  Serial.print("[Settings] Send interval: ");
  Serial.print(sendIntervalSec);
  Serial.println(" seconds");
  Serial.print("[Settings] Simulation mode: ");
  Serial.println(simulationMode ? "ON" : "OFF");

  startWifi();
  loraReady = initLoRa();
  readSensors();
  startWebServer();

  Serial.println("[Ready] Connect to AP FireNode and open http://192.168.4.1");
}

void loop() {
  server.handleClient();
  maintainWifiConnection();
  readSensorsIfNeeded();
  sendLoRaIfNeeded();
}
