# ADM FireNode Project Status

## Current Status
- Main RPi server 192.168.9.51 deployed and operational; dashboard works in LIVE mode.
- Node RPi 192.168.9.52 (NODE_01) deployed and operational; CSI camera works and appears on .51 main dashboard.
- Node RPi 192.168.9.53 (NODE_02) deployed and operational; CSI camera works and displays on local dashboard.
- Node RPi 192.168.9.54 (NODE_03) deployed and operational; CSI camera works and displays on local dashboard.
- ESP32 MAIN + NODE_01 bench validation PASSED.
- LoRa two-way communication confirmed between MAIN and NODE_01.
- Thermal camera hardware not installed yet (preserved in architecture).
- USB webcams are deprecated/removed from target design (historical blocker documented below).
- Raspberry Pi Camera Rev 1.3 (ov5647) via CSI is the official camera hardware.
- .51 MAIN: CSI camera detected successfully (`rpicam-hello --list-cameras`: ov5647 [2592x1944 10-bit GBRG]).
- .52 NODE_01: CSI camera detected successfully (same ov5647 sensor); stream visible on .51 dashboard.
- .53 NODE_02: CSI camera validated; `rpicam-hello --list-cameras` confirmed ov5647; local dashboard shows live CSI stream.
- .54 NODE_03: CSI camera validated; `rpicam-hello --list-cameras` confirmed ov5647; local dashboard shows live CSI stream.
- MAIN ESP32 is physically connected to .51 by USB serial at /dev/ttyUSB0.
- Minicom confirmed readable serial data at 115200 baud from MAIN ESP32.
- MAIN ESP32 receives LoRa packets from NODE_01.
- MAIN ESP32 USB serial integration implemented. Verification pending because MAIN .51 is currently unavailable.
- NODE_02 and NODE_03 required `python3-picamera2` and file sync (`app.py`, `static/app.js`, `templates/dashboard.html`, `modules/csi_camera_stream.py`, `modules/multi_camera_stream.py`, config).
- NODE_03 root cause: outdated `modules/multi_camera_stream.py` lacked CSI/Picamera2 stream logic; resolved by copying current file from NODE_01.

## Completed Validation
- Python tests passed
- Simulation smoke test passed
- PlatformIO 6.1.19 installed
- ESP32 sensor sender build passed
- ESP32 LoRa gateway build passed
- ESP32 MAIN + NODE_01 bench validation PASSED
- LoRa two-way MAIN ↔ NODE_01 communication PASSED (RSSI -29 to -35 dBm; SNR 9.25 to 10.00)
- DHT22, PIR, MQ analog, and LoRa TX/RX working on MAIN and NODE_01
- Thermal camera hardware not installed yet (preserved in architecture)
- NODE_02 and NODE_03 ESP32 hardware not yet available/assembled
- CSI camera hardware selection finalized and detection confirmed on .51, .52, .53, and .54
- .52 NODE_01 CSI camera stream confirmed on .51 main dashboard
- .53 NODE_02 CSI camera stream confirmed on local dashboard
- .54 NODE_03 CSI camera stream confirmed on local dashboard
- .51 can pull remote node data from .52
- MAIN ESP32 USB serial integration implemented (modules/esp32_serial_reader.py, app.py, config updates)
- NODE_01 camera visible on .51 main dashboard in LIVE mode
- Minicom confirmed live serial output at 115200 from MAIN ESP32
- NODE_02 and NODE_03 CSI camera setup and validation completed
- All three nodes (.52, .53, .54) display live CSI camera stream on their local dashboards
- `python3-picamera2` confirmed as required package on NODE_02 and NODE_03

## Next Incomplete Task
Validate NODE local ESP32 serial/UART status on NODE_03 (.54) and NODE_01 (.52). Verify ESP32 Local Serial card works: "Disconnected" before UART wiring, "Connected" with data after wiring. Also verify MAIN ESP32 USB serial integration on .51 RPi in live mode. (Blocked: MAIN .51 is currently unavailable; resume when reachable.)

## Immediate Goal
Verify that the MAIN RPi dashboard correctly displays sensor data from MAIN ESP32 USB serial for both local MAIN data and remote NODE_01 packets forwarded over LoRa, and that NODE_01 camera is visible on the MAIN dashboard in LIVE mode. This validation is pending because MAIN .51 is currently unavailable.

## Implementation Summary (2026-06-02)
- `modules/csi_camera_stream.py` created using Picamera2, JPEG output compatible with Flask MJPEG stream.
- `modules/multi_camera_stream.py` updated: CSI primary with USB fallback; simulation preserved.
- `app.py` DEFAULT_CONFIG updated: `camera_type="csi"`, 640x480@15fps, JPEG quality 85, `camera_usb_fallback` enabled.
- `requirements.txt` notes added for picamera2 via apt.
- `config.json` updated with new camera defaults.
- Dashboard UI labels updated from "USB Cameras" to generic "Camera".
- `py_compile` validation passed for all modified Python modules.

## ESP32 Serial Reader Implementation (2026-06-02 / 2026-06-08)
- **STATUS: IMPLEMENTED / VERIFICATION PENDING**
- `modules/esp32_serial_reader.py` created: thread-safe serial reader using pyserial.
- Parses lines containing `NODE=...` and caches latest per node ID.
- Ignores decorative lines (`===== LORA RX =====`, `[RSSI]`, `[SNR]`, etc.).
- Config keys added: `esp32_serial_enabled`, `esp32_serial_port`, `esp32_serial_baud`.
- `app.py` updated to import serial reader, start it in server live mode, and overlay serial data into local/remote node slots.
- `/api/status` exposes `serial_connected`, `serial_error`, `last_packet_time`, `packets_by_node`.
- `/api/config` POST allows updating serial settings.
- Dashboard mapping:
  - NODE=MAIN → FireNode-192-168-9-51 (local node)
  - NODE=NODE_01 → FireNode-192-168-9-52 (remote slot 1)
  - NODE=NODE_02 → FireNode-192-168-9-53 (remote slot 2) — pending hardware
  - NODE=NODE_03 → FireNode-192-168-9-54 (remote slot 3) — pending hardware
- HTTP ESP32 fallback preserved when serial is disabled or no data exists.
- `py_compile` and parsing unit tests passed.
- No camera, thermal, or ESP32 firmware changes made.
- **PENDING:** Live-mode validation with actual serial traffic on .51 hardware.

## Current Camera Finding
- USB webcam path is deprecated. Historical findings preserved for reference:
  - `/dev/video0` was the USB webcam device.
  - Default OpenCV capture read failed; V4L2 + MJPG manual test worked but produced distorted/corrupted frames.
  - RPi 3B USB bandwidth/power was suspected as the root cause.
- Official camera hardware: Raspberry Pi Camera Rev 1.3 (ov5647) via CSI ribbon.
- Confirmed detection command: `rpicam-hello --list-cameras`
- Detected sensor: `ov5647 [2592x1944 10-bit GBRG]`
- Detected modes: 640x480@58.92fps, 1296x972@46.34fps, 1920x1080@32.81fps, 2592x1944@15.63fps
- Current RPi OS: Raspberry Pi OS Legacy Lite 32-bit with Openbox via RDP.
- Next implementation step: validate rpicam/libcamera capture integration on .51 and .52 in deployed environment.
- USB microphone/chainsaw detection remains later work.

## Thermal Camera Status
- MLX90640 thermal camera is part of MAIN only.
- Hardware not yet installed on .51 but preserved in architecture.
- No removal or deprecation; remains future MAIN-only hardware.

## Current Deployment Support
- `scripts/deploy_main_server.sh`
- `scripts/deploy_node.sh`
- `scripts/deploy_all_rpis.sh`
- `docs/deployment/rpi_automated_deployment.md`

Targets:
- Main Server: `192.168.9.51`
- Node 1: `192.168.9.52`
- Node 2: `192.168.9.53`
- Node 3: `192.168.9.54`

Default mode:
- SSH key auth using `~/admfire`
- SSH user `betech`
- simulation mode enabled
- manual start by default
- optional systemd service file created but not enabled unless requested
- `deploy_all_rpis.sh` deploys all RPis in parallel by default
- `--sequential` deploys one RPi at a time
- `--target <ip>` deploys only one RPi
- per-target logs are written under `logs/deploy_<ip>.log`
- final summary prints pass/fail per RPi

Deployment role labels:
- `192.168.9.51`: `main_server`
- `192.168.9.52`: `node_01`
- `192.168.9.53`: `node_02`
- `192.168.9.54`: `node_03`

## Do Not Start Yet
- Major architecture refactor
- Camera/thermal integration changes
- Dashboard redesign (MAIN)
- Multi-node live integration changes (until serial is verified)
- ESP32/LoRa hardware validation (already done for MAIN + NODE_01)

## Separate Node Dashboard + Local Serial (2026-06-09 / 2026-06-10)
- Separate NODE GUI implemented for NODE RPis only (.52/.53/.54).
- NODE local ESP32 serial/UART status indicator added (2026-06-10): green/yellow/red ESP32 Local Serial card on node dashboard.
- app.py updated: esp32_serial_node_port config (/dev/serial0), node serial reader startup, local serial cache priority, /api/status local_serial fields.
- config.json updated with esp32_serial_node_port default.
- No ESP32 firmware changes. MAIN dashboard preserved.
- New files: `templates/node_dashboard.html`, `static/node_app.js`.
- Shared: `static/style.css`.
- NODE GUI is one-page only with local camera, sensor readings, chainsaw controls/status, alerts, recordings.
- MAIN server dashboard (`dashboard.html` + `app.js`) preserved unchanged.
- NODE simulation mode disabled: `operation_mode()` forced to `"live"` for node roles.
- Chainsaw controls moved from Tools tab into NODE dashboard page.
- `app.py` index() route: `current_role() == "node"` → `node_dashboard.html`; `"server"` → `dashboard.html`.
- No ESP32/LoRa/thermal architecture changes.
- `py_compile` all modules PASS.
