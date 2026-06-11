# ADM FireNode Active Context

Project: ADM FireNode Forest Monitoring System

Repo:
https://github.com/pagibetech/adm-firenode-forest-monitoring

Current synchronized branch:
main

Current known validation state:
- Main RPi server 192.168.9.51 deployed and operational; dashboard works in LIVE mode.
- Node RPi 192.168.9.52 (NODE_01) deployed and operational; CSI camera works and appears on .51 main dashboard.
- Node RPi 192.168.9.53 (NODE_02) deployed and operational; CSI camera works and displays on local dashboard.
- Node RPi 192.168.9.54 (NODE_03) deployed and operational; CSI camera works and displays on local dashboard.
- .51 MAIN: CSI camera detected successfully (ov5647 [2592x1944 10-bit GBRG]; `rpicam-hello --list-cameras`).
- .52 NODE_01: CSI camera detected successfully (same ov5647 sensor); appears on .51 main dashboard.
- .53 NODE_02: Raspberry Pi CSI Camera validated; `rpicam-hello --list-cameras` confirmed ov5647; local dashboard shows live CSI stream.
- .54 NODE_03: Raspberry Pi CSI Camera validated; `rpicam-hello --list-cameras` confirmed ov5647; local dashboard shows live CSI stream.
- ESP32 MAIN + NODE_01 bench validation PASSED.
- LoRa two-way communication confirmed: MAIN → NODE_01 PASS; NODE_01 → MAIN PASS; RSSI approx -29 to -35 dBm; SNR approx 9.25 to 10.00.
- DHT22, PIR, MQ analog, and LoRa TX/RX are working on MAIN and NODE_01.
- Battery ADC on MAIN appears floating/unconnected.
- NODE_02 and NODE_03 ESP32 hardware are not yet available/assembled; expected same wiring/firmware as NODE_01.
- MAIN ESP32 is physically connected to .51 by USB serial at /dev/ttyUSB0.
- Minicom confirmed readable serial data at 115200 baud from MAIN ESP32.
- MAIN ESP32 receives LoRa packets from NODE_01.
- NODE_02 and NODE_03 required `python3-picamera2` and sync of `app.py`, `static/app.js`, `templates/dashboard.html`, `modules/csi_camera_stream.py`, `modules/multi_camera_stream.py`, and node-specific config values.
- NODE_03 root cause: outdated `modules/multi_camera_stream.py` lacked CSI/Picamera2 stream logic; resolved by copying current file from NODE_01.
- MAIN SERVER .51 is currently unavailable, so centralized dashboard/live serial validation is still pending.

Example received packet (NODE_01 via LoRa to MAIN ESP32):
```
[RECEIVED] NODE=NODE_01,SEQ=1765,TEMP=27.20,HUM=63.20,PIR=0,MQ=2095,BAT=2926
```

Example MAIN local packet (MAIN ESP32 self-data):
```
[LORA TX OK] NODE=MAIN,SEQ=1765,TEMP=27.70,HUM=62.90,PIR=0,MQ=356,BAT=0
```

Current next incomplete milestone:
Validate NODE local ESP32 serial/UART status on NODE_03 (.54) and other nodes. Verify ESP32 Local Serial card works (shows "Disconnected" before UART wiring, "Connected" with sensor data after wiring). Also verify MAIN ESP32 USB serial integration on .51 RPi in live mode. (Blocked: MAIN .51 is currently unavailable.)

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
- 192.168.9.53 = Node 2 (FireNode-192-168-9-53) — CSI camera validated; ESP32 hardware pending assembly
- 192.168.9.54 = Node 3 (FireNode-192-168-9-54) — CSI camera validated; ESP32 hardware pending assembly

Current deployment mode:
- MacBook-run SSH deployment using key `~/admfire`
- SSH user `betech`
- Raspberry Pi app deployed in simulation/manual-start mode
- ESP32 MAIN + NODE_01 bench validated; NODE_02/NODE_03 pending hardware assembly
- MAIN ESP32 USB serial integration implemented; verification still pending.

Latest completed task (2026-06-10):
- Real audio validation pack added under test_audio_real/ with 10 FM-synthesized realistic WAV files in 3 categories:
  - positive_chainsaw/: chainsaw_start, chainsaw_cutting, chainsaw_idle, chainsaw_long (start→cut→idle cycle)
  - negative_non_chainsaw/: motorcycle, rain_wind, forest_ambient, human_voice, engine_generator
  - borderline/: brush_cutter
  All 44100 Hz mono 16-bit PCM, 8-18s each. README.md documents expected score ranges per file.
- NODE local ESP32 serial/UART status added to NODE dashboard.
- app.py updated: DEFAULT_CONFIG adds esp32_serial_node_port (/dev/serial0); main() starts serial reader for node role on GPIO UART; get_local_node_data() prioritizes local serial cache for node role; /api/status exposes local_serial fields (enabled, connected, port, error, last_packet_time, packets_by_node, cache_keys).
- NODE dashboard (node_dashboard.html + node_app.js) now shows ESP32 Local Serial card with green/yellow/red indicator near the top.
- NODE sensor readings source from local serial cache when available, else show "Waiting for data" placeholder.
- NODE GUI does not require "Scan ESP32 and Select" for local serial data.
- No ESP32 firmware changes. MAIN dashboard behavior preserved.
- py_compile validation passed for all modules.

Previous completed task (2026-06-09):
- Separate NODE GUI implemented: node_dashboard.html + node_app.js for NODE RPis only.
- MAIN server dashboard (dashboard.html + app.js) preserved unchanged.
- NODE GUI is one-page only (no tabs); shows local camera, sensor readings, chainsaw controls/status, alerts, recordings.
- NODE simulation mode disabled/removed: operation_mode() forced to "live" for node roles.
- Chainsaw controls moved from Tools tab into NODE dashboard page.
- app.py index() route checks current_role(): "node" → node_dashboard.html; "server" → dashboard.html.
- No ESP32/LoRa/thermal architecture changes.
- py_compile validation passed for all modules.

Previous completed task:
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
- NODE_02 (.53) and NODE_03 (.54) CSI camera setup and validation completed.
- All three nodes (.52, .53, .54) display live CSI camera stream on their local dashboards.
- NODE_02 required `python3-picamera2`, sync of `app.py`, `static/app.js`, `templates/dashboard.html`, `modules/csi_camera_stream.py`, `modules/multi_camera_stream.py`, and config node identity corrections.
- NODE_03 required `python3-picamera2`, sync of `app.py`, `modules/csi_camera_stream.py`, `modules/multi_camera_stream.py`, and config corrections; root cause was outdated `modules/multi_camera_stream.py`.
- Confirmed package requirement: `sudo apt install -y python3-picamera2`.
- Confirmed node configs:
  - NODE_02: ADM_FIRE_NODE_NAME=node_02, ADM_FIRE_NODE_IP=192.168.9.53, ADM_FIRE_ROLE=node_02
  - NODE_03: ADM_FIRE_NODE_NAME=node_03, ADM_FIRE_NODE_IP=192.168.9.54, ADM_FIRE_ROLE=node_03

Camera hardware history:
- USB webcam was a compatibility blocker (YUYV fails; MJPG distorted/corrupted on RPi 3B).
- Decision: replace USB webcam with Raspberry Pi Camera Rev 1.3 via CSI ribbon.
- Current path: implement rpicam/libcamera-based capture pipeline for production.

Thermal camera history:
- MLX90640 thermal camera is part of MAIN only; not yet installed but preserved in architecture.
- Thermal camera path remains unchanged; no removal.

ESP32 Serial Reader Integration (2026-06-02 / 2026-06-08 / 2026-06-10):
- **STATUS: IMPLEMENTED / NODE LOCAL SERIAL ADDED / VERIFICATION PENDING**
- Created modules/esp32_serial_reader.py to read ESP32 serial at /dev/ttyUSB0 (MAIN) or /dev/serial0 (NODE) at 115200 baud.
- Parses NODE=MAIN, NODE=NODE_01, NODE=NODE_02, NODE=NODE_03 packets; caches latest per node ID.
- Ignores decorative lines (===== LORA RX =====, [RSSI], [SNR], etc.).
- app.py now prioritizes serial cache in live mode for MAIN sensor data (cache["MAIN"]) and NODE sensor data (first non-MAIN cache entry).
- Remote node slots overlay serial data so NODE_01 appears when packets arrive.
- NODE local ESP32 serial/UART status indicator added to node dashboard: green=connected+data, yellow=connected waiting, red=error/disconnected.
- Config keys: esp32_serial_enabled, esp32_serial_port, esp32_serial_baud, esp32_serial_node_port.
- /api/status exposes local_serial fields: enabled, connected, port, error, last_packet_time, packets_by_node, cache_keys.
- py_compile and parsing unit tests passed.
- No camera, thermal, or ESP32 firmware changes made.
- **NOT YET VERIFIED ON HARDWARE:** Live-mode validation of sensor card population on .51 is still pending. NODE local serial validation pending UART wiring on .52/.53/.54.

Dashboard node mapping:
- NODE=MAIN → FireNode-192-168-9-51 (local node on MAIN RPi)
- NODE=NODE_01 → FireNode-192-168-9-52 (remote slot 1)
- NODE=NODE_02 → FireNode-192-168-9-53 (remote slot 2) — pending hardware
- NODE=NODE_03 → FireNode-192-168-9-54 (remote slot 3) — pending hardware

Next exact command:
- Verify NODE local ESP32 serial/UART status on NODE_03: curl -s --max-time 5 http://192.168.9.54:8090/api/status | head -c 2000
- Verify NODE local ESP32 serial/UART status on NODE_01: curl -s --max-time 5 http://192.168.9.52:8090/api/status | head -c 2000
- Confirm NODE dashboard shows ESP32 Local Serial card with green/yellow/red indicator.
- Confirm ESP32 Local Serial shows "Disconnected" before physical UART wiring, "Connected" with sensor data after wiring.
- Verify MAIN ESP32 USB serial integration on .51 RPi in live mode. (Blocked: MAIN .51 currently unavailable.)
- Confirm sensor cards populate from serial data for MAIN and NODE_01.
- Confirm NODE_01 camera visible on MAIN dashboard.
- Confirm LIVE mode working.
- Keep thermal camera path unchanged (hardware not installed yet).
- Keep ESP32/LoRa path unchanged.
- USB microphone/chainsaw detection remains later work.
- NODE_02/NODE_03 ESP32 hardware remains pending assembly.
