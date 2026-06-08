# ADM FireNode Active Context

Project: ADM FireNode Forest Monitoring System

Repo:
https://github.com/pagibetech/adm-firenode-forest-monitoring

Current synchronized branch:
main

Current known validation state:
- Main RPi server 192.168.9.51 deployed and operational; dashboard works in LIVE mode.
- Node RPi 192.168.9.52 (NODE_01) deployed and operational; CSI camera works and appears on .51 main dashboard.
- Node RPis 192.168.9.53 (NODE_02) and 192.168.9.54 (NODE_03) are pending hardware build; placeholders.
- .51 MAIN: CSI camera detected successfully (ov5647 [2592x1944 10-bit GBRG]; `rpicam-hello --list-cameras`).
- .52 NODE_01: CSI camera detected successfully (same ov5647 sensor); appears on .51 main dashboard.
- .53 NODE_02: Raspberry Pi Camera Rev 1.3 CSI target hardware installed; pending physical confirmation.
- .54 NODE_03: Raspberry Pi Camera Rev 1.3 CSI target hardware installed; pending physical confirmation.
- ESP32 MAIN + NODE_01 bench validation PASSED.
- LoRa two-way communication confirmed: MAIN → NODE_01 PASS; NODE_01 → MAIN PASS; RSSI approx -29 to -35 dBm; SNR approx 9.25 to 10.00.
- DHT22, PIR, MQ analog, and LoRa TX/RX are working on MAIN and NODE_01.
- Battery ADC on MAIN appears floating/unconnected.
- NODE_02 and NODE_03 ESP32 hardware are not yet available/assembled; expected same wiring/firmware as NODE_01.
- MAIN ESP32 is physically connected to .51 by USB serial at /dev/ttyUSB0.
- Minicom confirmed readable serial data at 115200 baud from MAIN ESP32.
- MAIN ESP32 receives LoRa packets from NODE_01.

Example received packet (NODE_01 via LoRa to MAIN ESP32):
```
[RECEIVED] NODE=NODE_01,SEQ=1765,TEMP=27.20,HUM=63.20,PIR=0,MQ=2095,BAT=2926
```

Example MAIN local packet (MAIN ESP32 self-data):
```
[LORA TX OK] NODE=MAIN,SEQ=1765,TEMP=27.70,HUM=62.90,PIR=0,MQ=356,BAT=0
```

Current next incomplete milestone:
Verify MAIN ESP32 USB serial integration on .51 RPi in live mode.

Current operating rule:
Continue only from the next incomplete task. Do not start new architecture work until workflow memory, workbook, and status files are updated.

Implemented:
- modules/csi_camera_stream.py created using Picamera2, JPEG output compatible with Flask MJPEG generator.
- modules/multi_camera_stream.py updated: CSI primary with USB fallback; simulation preserved.
- app.py DEFAULT_CONFIG updated: camera_type="csi", 640x480@15fps, JPEG quality 85.
- requirements.txt notes added for picamera2 via apt.
- config.json updated with new camera defaults.
- dashboard.html and app.js updated: generic "Camera" labels instead of "USB Cameras".
- py_compile validation passed for all modified Python modules.
- modules/esp32_serial_reader.py created to read MAIN ESP32 USB serial at /dev/ttyUSB0 115200.
- Parses NODE=MAIN and NODE=NODE_01 packets; caches latest per node ID.
- Ignores decorative lines (===== LORA RX =====, [RSSI], [SNR], etc.).
- app.py now prioritizes serial cache in live mode for MAIN sensor data.
- Remote node slots overlay serial data so NODE_01 appears when packets arrive.
- Config keys added: esp32_serial_enabled, esp32_serial_port, esp32_serial_baud.
- Status endpoint /api/status exposes serial_connected, serial_error, last_packet_time, packets_by_node.
- py_compile and parsing unit tests passed.
- No camera, thermal, or ESP32 firmware changes made.

Current deployment targets:
- 192.168.9.51 = Main Server (FireNode-192-168-9-51)
- 192.168.9.52 = Node 1 (FireNode-192-168-9-52)
- 192.168.9.53 = Node 2 (FireNode-192-168-9-53) — pending hardware build
- 192.168.9.54 = Node 3 (FireNode-192-168-9-54) — pending hardware build

Current deployment mode:
- MacBook-run SSH deployment using key `~/admfire`
- SSH user `betech`
- Raspberry Pi app deployed in simulation/manual-start mode
- ESP32 MAIN + NODE_01 bench validated; NODE_02/NODE_03 pending hardware assembly
- MAIN ESP32 USB serial integration implemented; verification still pending.

Latest completed task:
- ESP32 MAIN + NODE_01 bench validation PASSED.
- LoRa two-way communication confirmed between MAIN and NODE_01.
- DHT22, PIR, MQ analog, and LoRa TX/RX validated on MAIN and NODE_01.
- Thermal camera hardware not installed yet (preserved in architecture).
- USB webcam deprecated; final camera hardware selected: Raspberry Pi Camera Rev 1.3 CSI.
- .51 MAIN and .52 NODE_01 CSI camera detection confirmed.
- .52 NODE_01 CSI camera stream appears on .51 main dashboard.
- NODE_01 camera visible on .51 main dashboard in LIVE mode.
- .51 can pull remote node data from .52.
- MAIN ESP32 USB serial integration implemented (modules/esp32_serial_reader.py, app.py, config updates).
- Minicom confirmed readable serial data at 115200 from MAIN ESP32.
- MAIN ESP32 receives LoRa packets from NODE_01.
- LIVE mode working.

Camera hardware history:
- USB webcam was a compatibility blocker (YUYV fails; MJPG distorted/corrupted on RPi 3B).
- Decision: replace USB webcam with Raspberry Pi Camera Rev 1.3 via CSI ribbon.
- Current path: implement rpicam/libcamera-based capture pipeline for production.

Thermal camera history:
- MLX90640 thermal camera is part of MAIN only; not yet installed but preserved in architecture.
- Thermal camera path remains unchanged; no removal.

ESP32 Serial Reader Integration (2026-06-02 / 2026-06-08):
- **STATUS: IMPLEMENTED / VERIFICATION PENDING**
- Created modules/esp32_serial_reader.py to read MAIN ESP32 USB serial at /dev/ttyUSB0 115200.
- Parses NODE=MAIN and NODE=NODE_01 packets; caches latest per node ID.
- Ignores decorative lines (===== LORA RX =====, [RSSI], [SNR], etc.).
- app.py now prioritizes serial cache in live mode for MAIN sensor data.
- Remote node slots overlay serial data so NODE_01 appears when packets arrive.
- Config keys added: esp32_serial_enabled, esp32_serial_port, esp32_serial_baud.
- Status endpoint /api/status exposes serial_connected, serial_error, last_packet_time, packets_by_node.
- py_compile and parsing unit tests passed.
- No camera, thermal, or ESP32 firmware changes made.
- **NOT YET VERIFIED ON HARDWARE:** Live-mode validation of sensor card population on .51 is still pending.

Dashboard node mapping:
- NODE=MAIN → FireNode-192-168-9-51 (local node on MAIN RPi)
- NODE=NODE_01 → FireNode-192-168-9-52 (remote slot 1)
- NODE=NODE_02 → FireNode-192-168-9-53 (remote slot 2) — pending hardware
- NODE=NODE_03 → FireNode-192-168-9-54 (remote slot 3) — pending hardware

Next exact command:
- Verify MAIN ESP32 USB serial integration on .51 RPi in live mode.
- Confirm sensor cards populate from serial data for MAIN and NODE_01.
- Confirm NODE_01 camera visible on MAIN dashboard.
- Confirm LIVE mode working.
- Keep thermal camera path unchanged (hardware not installed yet).
- Keep ESP32/LoRa path unchanged.
- USB microphone/chainsaw detection remains later work.
- NODE_02/NODE_03 remain pending hardware assembly.
