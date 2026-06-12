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
- NODE03 (.54) UART READINESS VERIFIED: /dev/serial0 exists, serial reader connected, ESP32 Local Serial card shows "Waiting for UART data" (yellow). Next: wire ESP32 to NODE03 GPIO UART for live data.
- MAIN ESP32 USB serial integration on .51 RPi in live mode still pending. (Blocked: MAIN .51 is currently unavailable.)
- NODE01 (.52) and NODE02 (.53) UART readiness not yet verified.

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

Latest completed tasks (2026-06-10 / 2026-06-12):

### NODE GUI cleanup
- Removed "Scan ESP32 and Select" wording from NODE dashboard; replaced with "Waiting for UART data" neutral/yellow state.
- Removed Recent Recordings card (not implemented).
- Renamed "Open Folder" to "Browse RPi Folder" with helper text explaining in-page browsing behavior.

### Chainsaw detector UX
- Renamed "USB Mic Devices" to "Audio Input Devices" with device selection (Select button → POST input_device to /api/config).
- Added detector error row in chainsaw status card.
- Start Detection now shows "Starting..." (yellow) with delayed re-poll for runtime feedback.
- /api/start backend checks if detector thread died within 0.6s and reports started=false with error.

### Audio visualizer
- Added Audio Input Monitor section to chainsaw card: RMS level bar (green→orange→red), Peak bar, waveform canvas (green line on dark bg), score + sample rate meta.
- Fast-poll /api/audio-monitor every 600ms. Detector stores last audio buffer waveform (150 points) + peak in status.
- Shows contextual messages: no device selected, detector stopped, monitoring, error.

### Sample rate fix
- USB PnP Sound Device native rate 44100 Hz; detector config had 16000 Hz causing PaErrorCode -9997.
- detector._loop() now queries device default_samplerate and uses it when device selected.
- Actual sample_rate exposed via /api/audio-monitor and /api/status chainsaw block.

### Live device enumeration fix
- /api/devices was returning stale PortAudio-cached devices after USB mic unplugged.
- Replaced with subprocess arecord -l for real-time ALSA hardware query.
- Cross-references arecord output with sounddevice list by name for PortAudio-compatible indices.
- When arecord reports no capture hardware, returns empty device list.

### Real audio validation pack
- test_audio_validation/ created with positive_chainsaw/ (6 real Google Drive recordings converted to mono 44100Hz 16-bit clips), negative_non_chainsaw/, borderline/.
- Published docs/audio/CHAINSAW_AUDIO_AUDIT.md audit report covering 30 files across repo + Google Drive.
- Negative real-world samples still need manual download or phone recording.

### NODE03 validation
- Latest node dashboard deployed and operational on .54.
- /dev/serial0 exists and serial reader connected (local_serial.connected=true).
- UART enabled, waiting for ESP32 data packets.
- Camera operational (CSI ov5647, HTTP 200 on /video_feed).
- Audio visualizer and chainsaw detector UX verified on NODE03.

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

ESP32 Serial Reader Integration (2026-06-02 / 2026-06-08 / 2026-06-10 / 2026-06-12):
- **STATUS: IMPLEMENTED / NODE03 UART VERIFIED / MAIN .51 PENDING**
- Created modules/esp32_serial_reader.py to read ESP32 serial at /dev/ttyUSB0 (MAIN) or /dev/serial0 (NODE) at 115200 baud.
- Parses NODE=MAIN, NODE=NODE_01, NODE=NODE_02, NODE=NODE_03 packets; caches latest per node ID.
- Ignores decorative lines (===== LORA RX =====, [RSSI], [SNR], etc.).
- app.py now prioritizes serial cache in live mode for MAIN sensor data (cache["MAIN"]) and NODE sensor data (first non-MAIN cache entry).
- Remote node slots overlay serial data so NODE_01 appears when packets arrive.
- NODE local ESP32 serial/UART status indicator added to node dashboard: green=connected+data, yellow=connected waiting, red=error/disconnected.
- Config keys: esp32_serial_enabled, esp32_serial_port, esp32_serial_baud, esp32_serial_node_port.
- /api/status exposes local_serial fields: enabled, connected, port, error, last_packet_time, packets_by_node, cache_keys.
- NODE03 (.54) VERIFIED: /dev/serial0 exists, serial reader connected (local_serial.connected=true), waiting for ESP32 data.
- NODE01 (.52) and NODE02 (.53) UART not yet verified.
- py_compile and parsing unit tests passed.
- No camera, thermal, or ESP32 firmware changes made.
- **MAIN .51 verification still pending** (unavailable).

Dashboard node mapping:
- NODE=MAIN → FireNode-192-168-9-51 (local node on MAIN RPi)
- NODE=NODE_01 → FireNode-192-168-9-52 (remote slot 1)
- NODE=NODE_02 → FireNode-192-168-9-53 (remote slot 2) — pending hardware
- NODE=NODE_03 → FireNode-192-168-9-54 (remote slot 3) — pending hardware

Next exact command:
- Wire ESP32 NODE_03 to .54 RPi GPIO UART (pins 8/10: TXD/RXD ↔ ESP32 RXD/TXD, plus GND).
- Verify ESP32 Local Serial card turns green with live data after ESP32 transmits NODE=NODE_03 packets.
- Verify NODE local ESP32 serial/UART status on NODE_01 (.52) and NODE_02 (.53).
- Verify MAIN ESP32 USB serial integration on .51 RPi in live mode. (Blocked: MAIN .51 currently unavailable.)
- Negative real-world audio samples still needed (motorcycle, rain, wind, forest, voice, generator).
- Keep thermal camera path unchanged (hardware not installed yet).
- Keep ESP32/LoRa path unchanged.
- NODE_02/NODE_03 ESP32 hardware remains pending assembly.
