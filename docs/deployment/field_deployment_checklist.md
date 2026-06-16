# FireNode Field Deployment Checklist

Use this checklist after the simulation smoke test passes and before the forest demo.

## 1. Bench Preparation

- Charge each 12 V battery and label it for `main-center`, `node-01`, `node-02`, and `node-03`.
- Confirm each Raspberry Pi boots from its assigned SD card.
- Confirm each ESP32 sensor sender boots and exposes `/data` over Wi-Fi when used in live mode.
- Confirm the ESP32 LoRa gateway appears as a USB serial device on the main Raspberry Pi.
- Run the main simulation smoke test:

```bash
./scripts/smoke_test_main_simulation.py
```

## 2. Main / Center Node (.51)

- Install the main Raspberry Pi, daytime camera, MLX90640 thermal camera (future), siren relay, ESP32 LoRa gateway, and 12 V battery.
- Use a fused 12 V input and a stable 5 V buck converter rated for the Raspberry Pi load.
- Connect MAIN ESP32 to .51 RPi by USB serial at `/dev/ttyUSB0`.
- Start or install the web app service:

```bash
cd raspi/firenode-system
./run.sh
# or
./setup.sh --install-service
```

- Open the dashboard:

```text
http://<main-rpi-ip>:8090
```

- Verify MAIN ESP32 serial reader starts automatically in server live mode.
- Check `/api/status` and confirm `serial_connected: true` and `packets_by_node` includes `MAIN` and/or `NODE_01`.
- If using the ESP32 LoRa gateway over USB, the serial reader now handles sensor data directly; HTTP fallback remains available.

## 3. Remote Nodes

- Install one Raspberry Pi, one ESP32 sensor sender, one daytime camera, one microphone, one LoRa sender, and one 12 V battery per remote node.
- Verify camera stream locally on each node before placing it in the field.
- Verify sensor readings are reasonable: temperature, humidity, smoke raw/PPM, PIR/human, battery voltage.
- Verify chainsaw detector can start and stop from the node GUI or API.
- Place the remote nodes first at short range, then move outward after packets are stable.

## 4. LoRa Validation

- Check `/api/lora/status` on the main dashboard.
- Confirm all expected node IDs appear.
- Record RSSI, SNR, sequence increments, and PDR estimate.
- Run a 100-packet test per node before the final demo.
- Acceptance target: packet delivery ratio above 70% with RSSI/SNR logged.

## 5. Camera And Recording Validation

- On each RPi, confirm the CSI camera is detected:

```bash
rpicam-hello --list-cameras
```

Expected output should include `ov5647 [2592x1944 10-bit GBRG]`.

- USB webcam path is deprecated. Historical note: USB cameras showed YUYV failures and corrupted MJPG frames on RPi 3B; the project has moved to Raspberry Pi Camera Rev 1.3 via CSI.
- Ensure `python3-picamera2` is installed on every node:

```bash
sudo apt install -y python3-picamera2
```

- After confirming CSI detection, test a still capture:

```bash
rpicam-still -o /tmp/csi_test.jpg --width 1296 --height 972
```

- Once the rpicam/libcamera pipeline is integrated into the app, confirm the MJPEG stream endpoint:

```bash
curl -I --max-time 5 http://<rpi-ip>:8090/video_feed
```

- Confirm all four daytime camera feeds are visible on the main dashboard.
- Trigger or simulate a chainsaw event.
- Confirm the dashboard alert appears.
- Confirm a recording snapshot appears in the Recent Recordings panel.
- Confirm files are written under:

```text
raspi/firenode-system/media/events/
```

### CSI Camera Deployment Sync Checklist
When aligning a node to the current CSI camera pipeline, ensure these files and configs are synchronized:
- `app.py`
- `static/app.js`
- `templates/dashboard.html`
- `modules/csi_camera_stream.py`
- `modules/multi_camera_stream.py`
- `config.json` node-specific values
- `.deployment.env` node-specific values

## 6. ESP32 Serial Reader Validation (NEW)

- **DEPLOY FIRST:** Deploy updated `raspi/firenode-system` to .51 MAIN.
- Confirm `/dev/ttyUSB0` exists on .51:

```bash
ls -la /dev/ttyUSB0
```

- Confirm readable serial output with minicom:

```bash
minicom -D /dev/ttyUSB0 -b 115200
```

Expected lines:
```
[RECEIVED] NODE=NODE_01,SEQ=...,TEMP=...,HUM=...,PIR=...,MQ=...,BAT=...
[LORA TX OK] NODE=MAIN,SEQ=...,TEMP=...,HUM=...,PIR=...,MQ=...,BAT=...
```

- Confirm `/api/status` shows:
  - `serial_connected: true`
  - `last_packet_time` is recent
  - `packets_by_node` includes `MAIN` and/or `NODE_01`
- Confirm `/api/server-dashboard` sensor cards populate with serial data:
  - MAIN (local node) shows temperature, humidity, PIR, MQ, battery.
  - NODE_01 (remote slot 1) shows temperature, humidity, PIR, MQ, battery when LoRa packets are received.
- Confirm NODE_02 and NODE_03 remain placeholders (offline) until hardware is built.
- Confirm HTTP ESP32 fallback still works if serial is disabled.

## 8. NODE UART Verification (added 2026-06-12)

- [x] NODE03 (.54): Confirm `/dev/ttyUSB0` exists.
- [x] NODE03 (.54): Confirm UART enabled (`enable_uart=1` in /boot/config.txt).
- [x] NODE03 (.54): Confirm `curl /api/status` shows `local_serial.connected: true`.
- [x] NODE03 (.54): Confirm NODE GUI shows ESP32 Local Serial card with yellow "Waiting for UART data".
- [ ] NODE01 (.52): Confirm `/dev/ttyUSB0` exists and UART enabled.
- [ ] NODE02 (.53): Confirm `/dev/ttyUSB0` exists and UART enabled.

- Confirm smoke alert state from MQ2 or simulation.
- Confirm chainsaw alert state from microphone or test audio.
- Confirm thermal/human state from MLX90640 on the main node.
- Confirm siren relay behavior only after the team is ready for audible testing.
- Log all results in `docs/workbook/ADM_FireNode_Implementation_Workbook.xlsx`.

## 8. ESP32 Node Validation

- Validate MAIN ESP32 LoRa gateway and NODE_01 sensor sender before adding NODE_02/NODE_03.
- Confirm two-way LoRa communication: MAIN → NODE_01 and NODE_01 → MAIN.
- Confirm DHT22, PIR, MQ analog, and battery ADC readings are reasonable on each node.
- If battery ADC appears floating/unconnected, verify voltage divider wiring and ADC pin assignment.
- NODE_02 and NODE_03 ESP32 hardware are pending assembly; use same wiring/firmware as NODE_01 once hardware is ready.
- NOTE: NODE_02 and NODE_03 Raspberry Pi CSI cameras are already validated and operational; only ESP32 + LoRa + sensor modules remain pending assembly.

## 9. Shutdown

- Stop optional services before disconnecting power:

```bash
cd raspi/firenode-system
./stop_lora_gateway_service.sh
./stop_server.sh
```

- Power down each Raspberry Pi cleanly:

```bash
sudo shutdown now
```
