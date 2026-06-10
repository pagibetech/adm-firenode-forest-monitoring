# ADM FireNode AI Session Handoff

## Handoff Summary
The project has passed local software and firmware build validation. Codex is temporarily paused due to rate limits. Use VS Code + Roo Code + Kimi for small/medium tasks only.

Latest implementation (2026-06-10):
- NODE local ESP32 serial/UART status added to NODE dashboard.
- Each NODE RPi now shows a green/yellow/red ESP32 Local Serial card on its dashboard.
- app.py: DEFAULT_CONFIG adds esp32_serial_node_port (/dev/serial0); main() starts serial reader on GPIO UART for node roles; get_local_node_data() reads local serial cache; /api/status exposes local_serial fields.
- NODE GUI: node_app.js renders ESP32 Local Serial card with port, status, last packet time, node IDs, error info.
- NODE sensor readings prefer local serial data; no "Scan ESP32" required for local serial.
- No ESP32 firmware changes. MAIN dashboard unchanged.
- py_compile all modules PASS.

Latest hardware validation (2026-06-08 / 2026-06-09):
- ESP32 MAIN + NODE_01 bench validation PASSED
- LoRa two-way communication confirmed: MAIN → NODE_01 PASS; NODE_01 → MAIN PASS; RSSI approx -29 to -35 dBm; SNR approx 9.25 to 10.00
- DHT22, PIR, MQ analog, and LoRa TX/RX are working on MAIN and NODE_01
- Battery ADC on MAIN appears floating/unconnected
- NODE_02 and NODE_03 ESP32 hardware are not yet available/assembled
- USB webcams deprecated from target design; replaced by Raspberry Pi Camera Rev 1.3 CSI
- .51 MAIN: CSI camera detected successfully (ov5647 via `rpicam-hello --list-cameras`); dashboard works in LIVE mode.
- .52 NODE_01: CSI camera detected successfully (same ov5647 sensor); stream visible on .51 main dashboard.
- .53 NODE_02: CSI camera validated; `python3-picamera2` installed; live stream confirmed on local dashboard.
- .54 NODE_03: CSI camera validated; `python3-picamera2` installed; live stream confirmed on local dashboard after syncing `modules/multi_camera_stream.py`.
- MAIN ESP32 is physically connected to .51 by USB serial at /dev/ttyUSB0.
- Minicom confirmed readable serial data at 115200 baud from MAIN ESP32.
- MAIN ESP32 receives LoRa packets from NODE_01.
- MAIN ESP32 USB serial integration implemented; **verification pending because MAIN .51 is currently unavailable**.

## Next Task
Validate NODE local ESP32 serial/UART status on NODE_03 (.54) — curl /api/status to confirm local_serial fields, then verify ESP32 Local Serial card on NODE dashboard. Also verify MAIN ESP32 USB serial integration on .51 RPi in live mode. (Blocked: MAIN .51 is currently unavailable; resume when .51 is reachable.)

## Required First Checks
Before editing, inspect:
- docs/ACTIVE_CONTEXT.md
- docs/PROJECT_STATUS.md
- docs/AI_SESSION_HANDOFF.md
- docs/CODEX_RULES.md
- docs/AI_ROUTING_RULES.md
- docs/CODEX_LIMIT_STATUS.md
- docs/workbook/ADM_FireNode_Implementation_Workbook.xlsx

## Current Instruction
Main server is deployed successfully at `192.168.9.51`; dashboard/API are working in LIVE mode. ESP32 MAIN + NODE_01 bench is validated. NODE_02 (.53) and NODE_03 (.54) CSI camera setup and validation are completed; all three nodes display live CSI camera streams on their local dashboards. Do not modify firmware or architecture. The CSI camera code (`modules/csi_camera_stream.py` with Picamera2) is implemented and .51/.52/.53/.54 camera streams are working locally; NODE_01 camera is visible on the MAIN dashboard. MAIN ESP32 USB serial integration is implemented. Next step is verify on .51 that sensor cards populate from serial data for MAIN and NODE_01. Keep thermal camera path unchanged (hardware not installed yet). Keep ESP32/LoRa, and simulation fallback unchanged. USB microphone/chainsaw detection remains later work.

## Separate Node Dashboard + Local Serial (2026-06-09 / 2026-06-10)
- Separate NODE GUI implemented: `templates/node_dashboard.html` + `static/node_app.js` for NODE RPis only.
- MAIN server dashboard preserved: `templates/dashboard.html` + `static/app.js` unchanged.
- NODE GUI is one-page only (no tabs); shows local camera, sensor readings, chainsaw controls/status, alerts, recordings.
- NODE local ESP32 serial/UART status card added (2026-06-10): green/yellow/red indicator at top.
- NODE simulation mode disabled: `operation_mode()` forced to `"live"` for node roles.
- Chainsaw controls moved from Tools tab into NODE dashboard page.
- `app.py` index() route: `current_role() == "node"` → `node_dashboard.html`; `"server"` → `dashboard.html`.
- Config key `esp32_serial_node_port` (/dev/serial0) added for node GPIO UART serial.
- `/api/status` exposes `local_serial` object with enabled, connected, port, error, last_packet_time, packets_by_node, cache_keys.
- No ESP32/LoRa/thermal architecture changes.
- `py_compile` all modules PASS.

## Local Implementation Done (2026-06-02 / 2026-06-10)
- `modules/csi_camera_stream.py` created (Picamera2, JPEG, MJPEG generator).
- `modules/multi_camera_stream.py` updated (CSI primary, USB fallback, simulation preserved).
- `app.py` updated with `camera_type="csi"`, 640x480@15fps, JPEG quality 85, `camera_usb_fallback=True`.
- `requirements.txt` notes added for picamera2 via apt.
- `config.json` updated with new defaults.
- Dashboard UI labels updated to generic "Camera".
- **2026-06-10**: NODE local ESP32 serial/UART status added to NODE dashboard. app.py starts serial reader on /dev/serial0 for node roles. NODE sensor data sources from local serial cache. /api/status exposes local_serial fields.
- `py_compile` validation passed for all modified Python files.

## Latest Implementation Added (2026-06-02 / 2026-06-08 / 2026-06-10)
- `scripts/deploy_main_server.sh`
- `scripts/deploy_node.sh`
- `scripts/deploy_all_rpis.sh`
- `docs/deployment/rpi_automated_deployment.md`
- `deploy_all_rpis.sh` now supports parallel default deployment, `--sequential`, `--target <ip>`, per-IP logs, and final pass/fail summary.
- RPi app config now accepts deployment role aliases: `main_server`, `node_01`, `node_02`, `node_03`.
- ESP32 MAIN + NODE_01 bench validation completed.
- Camera hardware updated to Raspberry Pi Camera Rev 1.3 CSI; USB webcam deprecated.
- `modules/esp32_serial_reader.py` created: reads `/dev/ttyUSB0` at 115200, parses `NODE=...` packets, caches per node ID.
- `app.py` updated: overlays serial data into local and remote node slots in live mode; HTTP fallback preserved.
- Config keys added: `esp32_serial_enabled`, `esp32_serial_port`, `esp32_serial_baud`.
- `/api/status` exposes serial status fields.
- `py_compile` and parsing unit tests passed.
- **Status: IMPLEMENTED / NODE LOCAL SERIAL ADDED / VERIFICATION PENDING.**

## Expected Validation
- `bash -n` on all deployment scripts.
- `./scripts/deploy_all_rpis.sh` from the MacBook when RPis are reachable.
- Manual start on each RPi with `/home/betech/admfire/raspi/firenode-system/run.sh`.
- API checks against `/api/status`, `/api/config`, `/api/node-data`, `/api/server-dashboard`, and `/api/lora/status`.
- Stream placeholder checks against `/video_feed` and main `/thermal.png`.
- CSI camera validation: run `rpicam-hello --list-cameras` on target RPi, confirm ov5647 appears, then test still capture via rpicam-still or libcamera-vid pipeline.
- Dashboard camera route after CSI implementation: `curl -I --max-time 5 http://192.168.9.51:8090/video_feed`.
- **NODE_02/NODE_03 CSI validation (COMPLETED):**
  - Confirm `python3-picamera2` is installed: `sudo apt install -y python3-picamera2`.
  - Confirm `rpicam-hello --list-cameras` shows ov5647 on .53 and .54.
  - Confirm local dashboard on .53 and .54 shows live CSI stream.
  - Confirm `/api/node-data` on .53/.54 shows `camera_type=csi` and `video_urls` type `csi_camera`.
  - Deployment sync checklist: `app.py`, `static/app.js`, `templates/dashboard.html`, `modules/csi_camera_stream.py`, `modules/multi_camera_stream.py`, `config.json` node-specific values, `.deployment.env` node-specific values.
- **Serial validation (PENDING — blocked by .51 unavailability):**
  - Confirm `/dev/ttyUSB0` exists on .51.
  - Confirm minicom shows readable serial output at 115200.
  - Confirm `/api/status` shows `serial_connected: true` and `packets_by_node` includes MAIN and/or NODE_01.
  - Confirm `/api/server-dashboard` sensor cards populate with serial data for MAIN (local) and NODE_01 (remote slot 1).
  - Confirm NODE_01 camera is visible on MAIN dashboard in LIVE mode.
  - Confirm NODE_02 and NODE_03 remain placeholders (offline) until ESP32 hardware is built.

## Deployment Sync Checklist (for NODE_02/NODE_03 CSI alignment)
When aligning a new or outdated node to the current CSI camera pipeline, ensure these files and configs are synchronized:
- `app.py`
- `static/app.js`
- `templates/dashboard.html`
- `modules/csi_camera_stream.py`
- `modules/multi_camera_stream.py`
- `config.json` node-specific values
- `.deployment.env` node-specific values
- Package dependency: `sudo apt install -y python3-picamera2`

## Next Exact Command

```bash
cd "/Users/macbookm1max321tb/A_Design/A_Coding/ADM Fire"
# Deploy and validate MAIN ESP32 USB serial integration on .51 RPi in live mode
# Keep thermal camera path unchanged
# Keep ESP32/LoRa path unchanged
# NODE_02/NODE_03 ESP32 hardware remains pending assembly
# Note: MAIN .51 is currently unavailable; centralized validation is pending.
```
