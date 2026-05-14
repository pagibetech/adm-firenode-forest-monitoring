# FireNode ESP32 LoRa Gateway

This firmware turns an ESP32 + SX1278/Ra-02 module into a USB serial LoRa gateway for the main Raspberry Pi.

It listens for LoRa packets from remote FireNode sensor senders, adds gateway receive metadata, and prints one compact JSON object per serial line. The Raspberry Pi script `raspi/firenode-system/lora_gateway_serial.py` reads those lines and posts them to `/api/lora/ingest`.

## Wiring

| SX1278 / Ra-02 | ESP32 |
|---|---|
| VCC | 3.3 V only |
| GND | GND |
| SCK | GPIO 18 |
| MISO | GPIO 19 |
| MOSI | GPIO 23 |
| NSS / CS | GPIO 5 |
| RST | GPIO 14 |
| DIO0 | GPIO 26 |

Use a tuned 433 MHz antenna and a stable 3.3 V supply. Do not power the LoRa module from 5 V.

## Serial Output Example

```json
{"packet_id":"GW-REMOTE-01-1842","timestamp":"123456","node_id":"REMOTE-01","seq":1842,"slot":1,"rssi_dbm":-84,"snr_db":7.25,"frequency_mhz":433.00,"spreading_factor":7,"bandwidth_khz":125.0,"received":true,"payload":{"node_id":"REMOTE-01","temperature_c":34.2,"humidity_pct":58.1,"smoke_ppm":420,"smoke_detected":false,"pir_human":false,"battery_v":12.4}}
```

## Run With Raspberry Pi Main Server

On the Raspberry Pi main server:

```bash
cd raspi/firenode-system
python3 lora_gateway_serial.py --port /dev/ttyUSB0 --baud 115200 --api-base http://127.0.0.1:8090
```

## Notes

- This gateway does not need Wi-Fi.
- The sender firmware can continue sending the existing JSON packet. The gateway normalizes field names into the main server packet contract.
- If incoming packets do not contain `seq`, the gateway generates an incrementing sequence per received packet.
