# FireNode ESP32 PlatformIO v5 - PIR + compact web layout

# FireNode ESP32 LoRa Sensor Sender

PlatformIO project for an ESP32 WROOM-32 node with:

- DHT22 temperature and humidity sensor
- MQ2 smoke sensor digital output only
- PIR motion sensor for human/motion detection
- SX1278 / Ra-02 433 MHz LoRa module
- ESP32-hosted web GUI
- `/data` JSON endpoint
- Open AP SSID: `FireNode`
- AP + STA enabled at the same time
- Wi-Fi scan and connect page
- Saved Wi-Fi credentials using ESP32 Preferences/NVS
- Simulation mode for development without sensors
- Editable LoRa send interval, default 3 seconds

## Recommended wiring

| Module | Signal | ESP32 GPIO |
|---|---|---:|
| DHT22 | DATA | GPIO 27 |
| MQ2 module | DO | GPIO 34 |
| PIR motion sensor | OUT | GPIO 32 |
| SX1278 Ra-02 | SCK | GPIO 18 |
| SX1278 Ra-02 | MISO | GPIO 19 |
| SX1278 Ra-02 | MOSI | GPIO 23 |
| SX1278 Ra-02 | NSS / CS | GPIO 5 |
| SX1278 Ra-02 | RESET | GPIO 14 |
| SX1278 Ra-02 | DIO0 | GPIO 26 |

## Important power notes

- SX1278/Ra-02 is a 3.3 V module. Do not connect its pins to 5 V logic.
- Use a stable 3.3 V supply for the LoRa module.
- DHT22 normally needs a 10 kΩ pull-up resistor from DATA to 3.3 V if the module board does not already include one.
- MQ2 heater modules often need 5 V supply, but the DO signal connected to ESP32 must not exceed 3.3 V. Use a level shifter or voltage divider if the module outputs 5 V logic.
- PIR modules are commonly powered from 5 V, but the OUT signal connected to ESP32 GPIO32 must not exceed 3.3 V. If your PIR OUT pin is 5 V, use a voltage divider or level shifter.
- ESP32 GPIO34 is input-only and has no internal pull-up/down. The MQ2 digital output module must drive the signal cleanly.
- GPIO32 uses internal pulldown in this firmware for the PIR input. Default PIR logic is active HIGH.

## LoRa defaults

- Frequency: 433 MHz
- Spreading factor: 7
- Bandwidth: 125 kHz
- Coding rate: 4/5
- Sync word: 0x12
- TX power: 17 dBm
- CRC: enabled

## LoRa JSON packet example

```json
{
  "node_id": "FireNode-192-168-1-45",
  "sta_ip": "192.168.1.45",
  "ap_ip": "192.168.4.1",
  "temperature": 30.5,
  "humidity": 71.2,
  "smoke": 0,
  "smoke_detected": false,
  "pir": 0,
  "human_detected": false,
  "simulation": false,
  "uptime": 12345
}
```

`node_id` uses the ESP32 STA IP when connected. If STA is not connected yet, it uses the AP IP.

## How to upload

Open the folder in VS Code with PlatformIO installed, then run:

```bash
pio run
pio run --target upload
pio device monitor

# Optional only. Not required because the GUI is embedded in main.cpp.
pio run --target uploadfs
```

## First-time setup

1. Power the ESP32.
2. Connect your phone/laptop to the open Wi-Fi AP named `FireNode`.
3. Open `http://192.168.4.1`.
4. Press **Scan Wi-Fi**.
5. Select your 2.4 GHz Wi-Fi network.
6. Enter the password and press **Save & Connect**.
7. The dashboard will show the assigned STA IP after connection.

## Web endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| `/` | GET | Web dashboard |
| `/data` | GET | JSON sensor/status data |
| `/scan` | GET | JSON list of nearby Wi-Fi networks |
| `/wifi` | POST | Save and connect to Wi-Fi |
| `/forget-wifi` | POST | Clear saved Wi-Fi credentials |
| `/settings` | POST | Save simulation mode and send interval |
| `/send-test` | POST | Send one immediate LoRa packet |

## SPIFFS / uploadfs note

The web GUI is embedded directly inside `src/main.cpp`, so `pio run --target uploadfs` is not required. A small `data/README.txt` file is included only to prevent PlatformIO from failing if you run `uploadfs` by habit.

## Notes

- AP and STA are both enabled. The AP remains available even after the ESP32 connects to your Wi-Fi router.
- Simulation mode is useful when DHT22/MQ2/PIR sensors are not connected yet.
- MQ2 digital output behavior can vary by module. This firmware assumes smoke detected = digital LOW. If your MQ2 module behaves opposite, change `MQ2_ACTIVE_LOW` in `src/main.cpp` to `false`.

## v3 Stability Fix

This version fixes a problem that can make the web GUI slow when the SX1278/Ra-02 LoRa module is not connected or not detected. In the previous version, if `loraReady` was false, the firmware retried LoRa sending continuously instead of every configured interval. This caused very high `lora_fail_count`, repeated Serial Monitor messages, and delayed web access through the STA IP.

Also added a small test endpoint:

```text
http://<ESP32_STA_IP>/health
```

Use `/health` first if the main dashboard is slow to load.


## v4 PIR Human Detection Update

This version adds PIR motion sensor support for basic human/motion detection.

Default PIR pin:

```text
PIR OUT -> ESP32 GPIO32
```

The web dashboard, `/data` endpoint, and LoRa JSON packet now include:

```json
{
  "pir": 1,
  "human_detected": true
}
```

Default PIR logic is active HIGH. If your PIR module outputs LOW during motion, change this line in `src/main.cpp`:

```cpp
const bool PIR_ACTIVE_HIGH = true;
```

to:

```cpp
const bool PIR_ACTIVE_HIGH = false;
```
