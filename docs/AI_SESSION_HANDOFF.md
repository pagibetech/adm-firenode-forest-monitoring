# ADM FireNode AI Session Handoff

## Handoff Summary
The project has passed local software and firmware build validation. Codex is temporarily paused due to rate limits. Use VS Code + Roo Code + Kimi for small/medium tasks only.

Latest hardware validation (2026-06-08):
- ESP32 MAIN + NODE_01 bench validation PASSED
- LoRa two-way communication confirmed: MAIN → NODE_01 PASS; NODE_01 → MAIN PASS; RSSI approx -29 to -35 dBm; SNR approx 9.25 to 10.00
- DHT22, PIR, MQ analog, and LoRa TX/RX are working on MAIN and NODE_01
- Battery ADC on MAIN appears floating/unconnected
- NODE_02 and NODE_03 ESP32 hardware are not yet available/assembled
- USB webcams deprecated from target design; replaced by Raspberry Pi Camera Rev 1.3 CSI
- .51 MAIN: CSI camera detected successfully (ov5647 via `rpicam-hello --list-cameras`); dashboard works in LIVE mode.
- .52 NODE_01: CSI camera detected successfully (same ov5647 sensor); stream visible on .51 main dashboard.
- .51 can pull remote node data from .52.
- .53 NODE_02 / .54 NODE_03: Raspberry Pi Camera Rev 1.3 CSI target hardware installed; pending physical confirmation
- MAIN ESP32 is physically connected to .51 by USB serial at /dev/ttyUSB0.
- Minicom confirmed readable serial data at 115200 baud from MAIN ESP32.
- MAIN ESP32 receives LoRa packets from NODE_01.
- MAIN ESP32 USB serial integration implemented; **verification still pending**.

## Next Task
Verify MAIN ESP32 USB serial integration on .51 RPi in live mode.

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
Main server is deployed successfully at `192.168.9.51`; dashboard/API are working in LIVE mode. ESP32 MAIN + NODE_01 bench is validated. Do not modify firmware or architecture. The CSI camera code (`modules/csi_camera_stream.py` with Picamera2) is implemented and .51/.52 camera streams are working; NODE_01 camera is visible on the MAIN dashboard. MAIN ESP32 USB serial integration is implemented. Next step is verify on .51 that sensor cards populate from serial data for MAIN and NODE_01. Keep thermal camera path unchanged (hardware not installed yet). Keep ESP32/LoRa, and simulation fallback unchanged. USB microphone/chainsaw detection remains later work.

## Local Implementation Done (2026-06-02)
- `modules/csi_camera_stream.py` created (Picamera2, JPEG, MJPEG generator).
- `modules/multi_camera_stream.py` updated (CSI primary, USB fallback, simulation preserved).
- `app.py` updated with `camera_type="csi"`, 640x480@15fps, JPEG quality 85, `camera_usb_fallback=True`.
- `requirements.txt` notes added for picamera2 via apt.
- `config.json` updated with new defaults.
- Dashboard UI labels updated to generic "Camera".
- `py_compile` validation passed for all modified Python files.

## Latest Implementation Added (2026-06-02 / 2026-06-08)
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
- **Status: IMPLEMENTED / VERIFICATION PENDING.**

## Expected Validation
- `bash -n` on all deployment scripts.
- `./scripts/deploy_all_rpis.sh` from the MacBook when RPis are reachable.
- Manual start on each RPi with `/home/betech/admfire/raspi/firenode-system/run.sh`.
- API checks against `/api/status`, `/api/config`, `/api/node-data`, `/api/server-dashboard`, and `/api/lora/status`.
- Stream placeholder checks against `/video_feed` and main `/thermal.png`.
- CSI camera validation: run `rpicam-hello --list-cameras` on target RPi, confirm ov5647 appears, then test still capture via rpicam-still or libcamera-vid pipeline.
- Dashboard camera route after CSI implementation: `curl -I --max-time 5 http://192.168.9.51:8090/video_feed`.
- **Serial validation (PENDING):**
  - Confirm `/dev/ttyUSB0` exists on .51.
  - Confirm minicom shows readable serial output at 115200.
  - Confirm `/api/status` shows `serial_connected: true` and `packets_by_node` includes MAIN and/or NODE_01.
  - Confirm `/api/server-dashboard` sensor cards populate with serial data for MAIN (local) and NODE_01 (remote slot 1).
  - Confirm NODE_01 camera is visible on MAIN dashboard in LIVE mode.
  - Confirm NODE_02 and NODE_03 remain placeholders (offline) until hardware is built.

## Next Exact Command

```bash
cd "/Users/macbookm1max321tb/A_Design/A_Coding/ADM Fire"
# Deploy and validate MAIN ESP32 USB serial integration on .51 RPi in live mode
# Keep thermal camera path unchanged
# Keep ESP32/LoRa path unchanged
# NODE_02/NODE_03 remain pending hardware assembly
```
