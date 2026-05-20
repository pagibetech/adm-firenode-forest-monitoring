# FireNode RPi Unified Main Server / Node System

This version updates the previous RPi node program so it can be used as the **main server RPi** for the forest FireNode system.

It is still a single package, but the default role is now **Main Server**. If you install the same package on the other three RPis, set those RPis to **Node** mode in the Settings tab.

---

## Main changes in this version

- Main Server dashboard is now the default role.
- Dashboard tab displays:
  - this main server's own USB webcam stream/s,
  - this main server's MLX90640 thermal camera stream,
  - remote video streams from the three other RPi nodes,
  - sensor data per node,
  - chainsaw alerts,
  - PIR human alerts,
  - thermal human alerts,
  - smoke alerts.
- Node Detail tab has a dropdown to select which node to view.
- Settings tab now includes:
  - Main Server / Node mode,
  - ESP32 scan/select,
  - remote RPi node scan,
  - multiple local USB webcam indexes,
  - MLX90640 thermal camera settings,
  - Wi-Fi settings reference and apply-command preview.
- The attached MLX90640 human-detection test program was integrated into the main app.
- Manual start is preserved. Running `./setup.sh` does **not** install autostart unless you explicitly run `./setup.sh --install-service`.

---

## Recommended deployment for your 4-RPi setup

### Main server RPi

- Run this updated program.
- Keep Role = **Main Server**.
- Connect its USB webcam/s.
- Connect the MLX90640 thermal camera through I2C.
- Click **Scan RPi Nodes** so it can find the other three RPis.

### Three remote node RPis

Each remote node should run a FireNode RPi app that exposes:

```text
http://<node-rpi-ip>:8090/api/node-data
http://<node-rpi-ip>:8090/video_feed
```

If you install this same updated package on the three remote RPis, set their Role to **Node** in the Settings tab.

---

## Folder structure

```text
firenode_rpi_system/
├── app.py
├── config.json
├── detector.py
├── requirements.txt
├── setup.sh
├── run.sh
├── install_service.sh
├── uninstall_service.sh
├── check_mic.sh
├── modules/
│   ├── alert_logger.py
│   ├── camera_stream.py
│   ├── esp32_client.py
│   ├── esp32_scanner.py
│   ├── multi_camera_stream.py
│   ├── network_utils.py
│   ├── node_registry.py
│   └── thermal_camera.py
├── templates/
│   └── dashboard.html
├── static/
│   ├── app.js
│   └── style.css
├── test_audio/
└── logs/
```

---

## Installation

Copy the ZIP file to the Raspberry Pi, extract it, then run:

```bash
cd firenode_rpi_system
chmod +x setup.sh
./setup.sh
```

The setup script installs the required packages for:

- Flask web server,
- OpenCV USB camera streaming,
- USB microphone chainsaw detection,
- MLX90640 thermal camera support,
- I2C tools,
- Pillow image output,
- Adafruit MLX90640 Python library.

After setup, reboot if I2C was newly enabled:

```bash
sudo reboot
```

---

## Manual run

```bash
cd firenode_rpi_system
./run.sh
```

Open the web GUI:

```text
http://<RPi-IP>:8090
```

Example:

```text
http://192.168.9.80:8090
```

---

## Optional autostart

Autostart is **not** installed by default.

Only use this if you later want the web app to start automatically on boot:

```bash
./setup.sh --install-service
```

Remove autostart:

```bash
./uninstall_service.sh
```

Install the optional LoRa serial gateway bridge after the ESP32/SX127x gateway is connected over USB:

```bash
./install_lora_gateway_service.sh /dev/ttyUSB0 115200 http://127.0.0.1:8090
```

Check gateway logs:

```bash
sudo journalctl -u firenode-lora-gateway.service -f
```

Stop the gateway bridge:

```bash
./stop_lora_gateway_service.sh
```

---

## Main server setup workflow

1. Start the program with:

   ```bash
   ./run.sh
   ```

2. Open the GUI:

   ```text
   http://<main-server-rpi-ip>:8090
   ```

3. Go to **Settings**.

4. Confirm Role is **Main Server**.

5. If this main server also has an ESP32 attached to the same Wi-Fi/LAN:
   - Click **Scan ESP32 FireNodes**.
   - Select the ESP32 assigned to the main server.

6. Enter local USB webcam indexes:

   ```text
   0
   ```

   or for multiple webcams:

   ```text
   0,2
   ```

   Check camera indexes with:

   ```bash
   v4l2-ctl --list-devices
   ls /dev/video*
   ```

7. Configure MLX90640 thermal settings.

8. Click **Scan RPi Nodes** to find the three remote nodes.

9. Confirm the Dashboard tab displays all local and remote streams.

---

## MLX90640 wiring reminder

Typical Raspberry Pi I2C wiring:

```text
MLX90640 VIN/VCC -> RPi 3.3V
MLX90640 GND     -> RPi GND
MLX90640 SDA     -> RPi GPIO2 / SDA / Pin 3
MLX90640 SCL     -> RPi GPIO3 / SCL / Pin 5
```

Check if the sensor is detected:

```bash
i2cdetect -y 1
```

Expected address is usually:

```text
0x33
```

If the sensor is not detected, the web app can still run, but thermal view will fall back to simulation if simulation mode is enabled or if initialization fails.

---

## Important URLs

Main web GUI:

```text
http://<RPi-IP>:8090
```

Local node JSON API:

```text
http://<RPi-IP>:8090/api/node-data
```

Primary USB webcam stream:

```text
http://<RPi-IP>:8090/video_feed
```

Specific USB webcam stream:

```text
http://<RPi-IP>:8090/video_feed/0
http://<RPi-IP>:8090/video_feed/2
```

MLX90640 thermal stream:

```text
http://<RPi-IP>:8090/thermal_feed
```

MLX90640 still PNG:

```text
http://<RPi-IP>:8090/thermal.png
```

Main server dashboard API:

```text
http://<main-server-rpi-ip>:8090/api/server-dashboard
```

---

## Wi-Fi settings note

The GUI has Wi-Fi fields because you requested Wi-Fi settings inside the Settings tab. For safety, the app stores the values and shows the commands to apply them manually. It does **not** automatically change Wi-Fi because doing so from the web GUI can disconnect the RPi and make it unreachable.

To generate apply commands:

1. Open **Settings**.
2. Enter SSID, password, country, and interface.
3. Click **Show Apply Commands**.
4. Run the displayed commands directly in the RPi terminal.

---

## Practical troubleshooting

### Camera not showing

Check camera device list:

```bash
v4l2-ctl --list-devices
ls /dev/video*
```

Try changing Camera Device Indexes in Settings.

If `/dev/video0` exists but the dashboard says `Camera frame read failed`, test the same MJPG/V4L2 mode used by the app:

```bash
cd /home/betech/admfire/raspi/firenode-system
./venv/bin/python camera_test.py --device 0 --fourcc MJPG --width 640 --height 480 --fps 25
```

Expected result:

```text
Camera test passed.
Saved test frame: /tmp/firenode_camera_test.jpg
```

The app defaults are:

```json
{
  "camera_backend": "V4L2",
  "camera_fourcc": "MJPG",
  "camera_open_warmup_frames": 5,
  "camera_retry_on_failed_read": true
}
```

### Thermal not showing

Check I2C:

```bash
i2cdetect -y 1
```

Make sure I2C is enabled and the MLX90640 appears at `0x33`.

### Main server does not find remote RPis

Make sure each remote RPi app is running:

```text
http://<remote-rpi-ip>:8090/api/node-data
```

If scan does not find them, manually enter the remote RPi IPs in Settings:

```text
192.168.9.51
192.168.9.52
192.168.9.53
```

### ESP32 not found

Make sure the ESP32 `/data` endpoint works:

```text
http://<esp32-ip>/data
```

---

## Notes on detection

The chainsaw detector is still a lightweight sound-pattern detector, not a trained machine-learning model.

The MLX90640 human detector uses simple thermal thresholds and blob size detection:

- Human Min Temp °C
- Human Max Temp °C
- Min Above Ambient °C
- Min Blob Pixels

Tune these values at the actual forest installation site.
