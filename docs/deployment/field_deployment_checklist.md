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

## 2. Main / Center Node

- Install the main Raspberry Pi, daytime camera, MLX90640 thermal camera, siren relay, ESP32 LoRa gateway, and 12 V battery.
- Use a fused 12 V input and a stable 5 V buck converter rated for the Raspberry Pi load.
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

- If using the ESP32 LoRa gateway over USB, install the bridge:

```bash
./install_lora_gateway_service.sh /dev/ttyUSB0 115200 http://127.0.0.1:8090
```

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

- On each RPi, confirm the USB camera can read MJPG frames:

```bash
cd /home/betech/admfire/raspi/firenode-system
./venv/bin/python camera_test.py --device 0 --fourcc MJPG --width 320 --height 240 --fps 10
```

- If the image is corrupted/unclear, keep lower camera settings first because Raspberry Pi 3B USB bandwidth or camera power may be limited.
- Confirm all four daytime camera feeds are visible on the main dashboard.
- Trigger or simulate a chainsaw event.
- Confirm the dashboard alert appears.
- Confirm a recording snapshot appears in the Recent Recordings panel.
- Confirm files are written under:

```text
raspi/firenode-system/media/events/
```

## 6. Alert Validation

- Confirm smoke alert state from MQ2 or simulation.
- Confirm chainsaw alert state from microphone or test audio.
- Confirm thermal/human state from MLX90640 on the main node.
- Confirm siren relay behavior only after the team is ready for audible testing.
- Log all results in `docs/workbook/ADM_FireNode_Implementation_Workbook.xlsx`.

## 7. Shutdown

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
