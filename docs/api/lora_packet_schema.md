# FireNode LoRa Packet And API Schema

This document is the implementation contract between:

- ESP32 sensor sender firmware
- ESP32 LoRa gateway firmware
- Raspberry Pi `lora_gateway_serial.py`
- Raspberry Pi `/api/lora/ingest`
- Dashboard and SQLite packet store

## Sender Payload

The remote ESP32 sensor sender transmits a compact JSON payload over LoRa.

```json
{
  "node_id": "REMOTE-01",
  "seq": 1842,
  "temperature": 34.2,
  "humidity": 58.1,
  "smoke": 420,
  "smoke_detected": false,
  "pir": 0,
  "human_detected": false,
  "battery_v": 12.4,
  "simulation": false,
  "uptime": 9281
}
```

Required fields for real deployment:

| Field | Type | Notes |
|---|---|---|
| `node_id` | string | Stable node ID, such as `REMOTE-01` |
| `seq` | integer | Monotonic packet sequence for PDR/loss checks |
| `temperature` | number/null | Celsius |
| `humidity` | number/null | Percent |
| `smoke` | number | Raw or PPM-like smoke value |
| `smoke_detected` | boolean | MQ2 threshold state |
| `human_detected` | boolean | PIR state |
| `battery_v` | number/null | Battery voltage after calibrated divider |

## Gateway Serial Line

The ESP32 LoRa gateway wraps each received sender payload with receiver metadata and prints one JSON object per serial line.

```json
{
  "packet_id": "GW-REMOTE-01-1842",
  "timestamp": "123456",
  "node_id": "REMOTE-01",
  "node_name": "REMOTE-01",
  "slot": 1,
  "seq": 1842,
  "rssi_dbm": -84,
  "snr_db": 7.25,
  "frequency_mhz": 433.0,
  "spreading_factor": 7,
  "bandwidth_khz": 125.0,
  "received": true,
  "payload": {
    "node_id": "REMOTE-01",
    "temperature_c": 34.2,
    "humidity_pct": 58.1,
    "smoke_ppm": 420,
    "smoke_detected": false,
    "pir_human": false,
    "battery_v": 12.4,
    "raw_sender_packet": "{...}"
  }
}
```

Gateway status lines are allowed and ignored by the Pi adapter:

```json
{"gateway_status":"ready","frequency_mhz":433.0}
```

## Raspberry Pi Ingest API

Endpoint:

```text
POST /api/lora/ingest
Content-Type: application/json
```

Response:

```json
{
  "ok": true,
  "stored": true,
  "packet_id": "GW-REMOTE-01-1842"
}
```

Duplicate `packet_id` values are ignored and return `stored: false`.

## Packet History API

Endpoint:

```text
GET /api/lora/packets?limit=100
```

Response:

```json
{
  "ok": true,
  "stored_packet_count": 128,
  "packets": []
}
```

## Status API

Endpoint:

```text
GET /api/lora/status
```

Simulation response includes:

```json
{
  "ok": true,
  "enabled": true,
  "simulation": true,
  "active_nodes": 4,
  "packet_count": 16,
  "stored_packet_count": 128,
  "average_pdr_estimate_pct": 93.5,
  "latest": []
}
```

## SQLite Table

Table: `lora_packets`

| Column | Purpose |
|---|---|
| `packet_id` | Unique packet key |
| `rx_ts` | Receive timestamp |
| `node_id`, `node_name`, `slot` | Node identity |
| `seq` | Packet sequence |
| `rssi_dbm`, `snr_db`, `pdr_estimate_pct` | Link metrics |
| `frequency_mhz` | Radio frequency |
| `payload_json` | Normalized payload |
| `raw_json` | Complete received packet |
| `accepted` | 1 if accepted |

## Validation Targets

- Dashboard update cadence: within 60 seconds for routine telemetry.
- Alert packet handling: immediate on smoke/chainsaw/thermal alert.
- PDR target: above 70% during field test.
- Each field test should record RSSI, SNR, sequence gaps, and node position.
