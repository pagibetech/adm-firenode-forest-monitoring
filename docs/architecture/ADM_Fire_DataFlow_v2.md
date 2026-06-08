# ADM FireNode Data Flow v2

**Version:** 2.0  
**Date:** 2026-06-08  
**Status:** Active — MAIN ESP32 USB serial integration implemented; verification pending.

## Overview

ADM FireNode is a four-node hybrid LoRa + Wi-Fi forest monitoring system. The main center node aggregates sensor telemetry, camera feeds, and alert states from itself and three remote nodes. The MAIN RPi reads its local ESP32's sensor data via USB serial instead of HTTP API, while remote node data arrives either via LoRa through the MAIN ESP32 (serial) or via HTTP from remote RPis.

## Node Roles

| IP | Role | Name | Status |
|---|---|---|---|
| 192.168.9.51 | Main Server / Center | FireNode-192-168-9-51 | Active, LIVE mode |
| 192.168.9.52 | Remote Node 1 | FireNode-192-168-9-52 | Active, camera on main dashboard |
| 192.168.9.53 | Remote Node 2 | FireNode-192-168-9-53 | Pending hardware build |
| 192.168.9.54 | Remote Node 3 | FireNode-192-168-9-54 | Pending hardware build |

## Data Paths

### 1. Sensor Telemetry (LoRa)

```
+-------------+      LoRa 433MHz      +-------------+      USB Serial      +-------------+
| NODE_01     |  ------------------>  | MAIN ESP32  |  ----------------->  | .51 MAIN    |
| ESP32       |   DHT, PIR, MQ, BAT   | (Gateway)   |   /dev/ttyUSB0       | RPi         |
+-------------+                       +-------------+   115200 baud        +-------------+
                                              ^                               |
                                              |                               | Serial parse
+-------------+      LoRa 433MHz             |                               v
| NODE_02     |  ------------------>         |                        +-------------+
| ESP32       |   (pending hw)               |                        | Dashboard   |
+-------------+                              |                        | Sensor Cards|
                                             |                        +-------------+
+-------------+      LoRa 433MHz             |
| NODE_03     |  ------------------>         |
| ESP32       |   (pending hw)               |
+-------------+                              |
                                             |
+-------------+      Local sensors           |
| MAIN ESP32  |  (self-data: DHT, PIR, MQ)   |
+-------------+                              |
```

**Key points:**
- Remote node ESP32s send sensor packets via LoRa to MAIN ESP32.
- MAIN ESP32 forwards received packets over USB serial to .51 RPi.
- MAIN ESP32 also sends its own local sensor data over the same serial line.
- `modules/esp32_serial_reader.py` on .51 reads `/dev/ttyUSB0` at 115200, parses packets, and caches per node ID.
- Dashboard maps:
  - `NODE=MAIN` → local node sensor card (.51)
  - `NODE=NODE_01` → remote slot 1 (.52)
  - `NODE=NODE_02` → remote slot 2 (.53) — pending hardware
  - `NODE=NODE_03` → remote slot 3 (.54) — pending hardware

### 2. Camera Feeds (Wi-Fi)

```
+-------------+      Wi-Fi / HTTP      +-------------+
| .51 MAIN    |  <------------------   | .52 NODE_01 |
| RPi         |    MJPEG stream        | RPi         |
| Dashboard   |                        | CSI Camera  |
+-------------+                        +-------------+
       ^
       |  (local CSI camera)
+------+------+
| .51 MAIN    |
| CSI Camera  |
+-------------+

+-------------+      Wi-Fi / HTTP      +-------------+
| .51 MAIN    |  (pending hw build)    | .53 NODE_02 |
| Dashboard   |                        | RPi + CSI   |
+-------------+                        +-------------+

+-------------+      Wi-Fi / HTTP      +-------------+
| .51 MAIN    |  (pending hw build)    | .54 NODE_03 |
| Dashboard   |                        | RPi + CSI   |
+-------------+                        +-------------+
```

**Key points:**
- Each node has a Raspberry Pi Camera Rev 1.3 (ov5647) via CSI ribbon.
- Camera streams are served over HTTP MJPEG from each node.
- .51 MAIN dashboard displays all camera feeds (local + remote).
- USB webcam path is deprecated; CSI is the official camera hardware.

### 3. Remote Node Data (HTTP Fallback)

```
+-------------+      HTTP API          +-------------+
| .51 MAIN    |  <------------------   | .52 NODE_01 |
| RPi         |   /api/node-data       | RPi         |
| (app.py)    |                        | (app.py)    |
+-------------+                        +-------------+
```

**Key points:**
- .51 can pull remote node data from .52 via HTTP API.
- This path is used for remote node health/status when serial data is not available.
- Serial data overlays and takes priority when packets are received from MAIN ESP32.

### 4. Thermal Camera (Future, MAIN Only)

```
+-------------+      I2C               +-------------+
| .51 MAIN    |  <------------------   | MLX90640    |
| RPi         |                        | Thermal Cam |
+-------------+                        +-------------+
```

**Key points:**
- MLX90640 thermal camera is MAIN ONLY.
- Not yet physically installed but preserved in architecture.
- Will be used for 360-degree thermal scan with servo in future milestone.
- No removal or deprecation.

### 5. Alert and Recording Flow

```
+-------------+      Alert trigger     +-------------+
| Sensor      |  ------------------>   | Dashboard   |
| (MQ, PIR,   |                        | Alert Panel |
|  thermal)   |                        +-------------+
+-------------+                               |
                                              v
                                       +-------------+
                                       | Event       |
                                       | Recorder    |
                                       +-------------+
                                              |
                                              v
                                       +-------------+
                                       | media/      |
                                       | events/     |
                                       +-------------+
```

## Serial Packet Format

Lines read from `/dev/ttyUSB0` at 115200 baud:

```
[RECEIVED] NODE=NODE_01,SEQ=1765,TEMP=27.20,HUM=63.20,PIR=0,MQ=2095,BAT=2926
[LORA TX OK] NODE=MAIN,SEQ=1765,TEMP=27.70,HUM=62.90,PIR=0,MQ=356,BAT=0
```

Parsed fields:
| Field | Key | Type | Example |
|---|---|---|---|
| Node ID | `node_id` | string | MAIN, NODE_01 |
| Sequence | `seq` | int | 1765 |
| Temperature | `temperature` | float | 27.20 |
| Humidity | `humidity` | float | 63.20 |
| PIR | `pir` | int | 0 |
| MQ (smoke) | `mq` | int | 2095 |
| Battery | `bat` | int | 2926 |

Decorative lines (e.g., `===== LORA RX =====`, `[RSSI] -38`, `[SNR] 9.5`) are ignored by the parser.

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/status` | System status including `serial_connected`, `serial_error`, `last_packet_time`, `packets_by_node` |
| `GET /api/config` | Current configuration |
| `POST /api/config` | Update configuration (including `esp32_serial_enabled`, `esp32_serial_port`, `esp32_serial_baud`) |
| `GET /api/node-data` | Local node sensor data (from serial cache if available) |
| `GET /api/server-dashboard` | Full dashboard payload with local + remote slots |
| `GET /api/lora/status` | LoRa packet store status |
| `GET /video_feed` | MJPEG camera stream |
| `GET /thermal.png` | Thermal camera image (future) |

## Configuration Keys (Serial)

| Key | Default | Description |
|---|---|---|
| `esp32_serial_enabled` | `true` | Enable USB serial reader on MAIN RPi |
| `esp32_serial_port` | `/dev/ttyUSB0` | USB serial device path |
| `esp32_serial_baud` | `115200` | Baud rate (matches ESP32 firmware) |

## Pending Work

- [x] MAIN ESP32 USB serial integration implemented.
- [ ] Verify MAIN ESP32 USB serial integration on .51 in live mode.
- [ ] Confirm sensor cards populate from serial data for MAIN and NODE_01.
- [ ] Confirm NODE_01 camera is visible on MAIN dashboard in LIVE mode.
- [ ] Confirm NODE_02 and NODE_03 remain placeholders until hardware is built.
- [ ] MLX90640 thermal camera installation and integration (future milestone).
- [ ] USB microphone and chainsaw detection (future milestone).
- [ ] 360-degree servo thermal scan (future milestone).

## Historical Notes

- USB webcam was deprecated due to YUYV failures and corrupted MJPG frames on RPi 3B.
- CSI camera (Raspberry Pi Camera Rev 1.3, ov5647) is now the official camera hardware.
- ESP32/LoRa hardware validation passed for MAIN + NODE_01; NODE_02/NODE_03 pending assembly.
