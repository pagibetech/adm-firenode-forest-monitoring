# ADM FireNode Project Status

## Current Status
Main server deployment is successful. Dashboard/API are working on `192.168.9.51`.

## Completed Validation
- Python tests passed
- Simulation smoke test passed
- PlatformIO 6.1.19 installed
- ESP32 sensor sender build passed
- ESP32 LoRa gateway build passed

## Next Incomplete Task
Deploy the USB camera capture fix to the main server and validate `/dev/video0` MJPG/V4L2 capture.

## Immediate Goal
Fix live USB webcam capture on the main server without changing thermal, simulation, or ESP32/LoRa behavior.

## Current Camera Finding
- `/dev/video0` is correct on the main server.
- The camera supports MJPG and YUYV.
- Default OpenCV capture read fails.
- `cv2.VideoCapture("/dev/video0", cv2.CAP_V4L2)` with MJPG, 640x480, 25 FPS works manually.
- The app now supports configurable `camera_backend`, `camera_fourcc`, `camera_open_warmup_frames`, and `camera_retry_on_failed_read`.
- Current RPi 3B stability defaults are `320x240`, `10 FPS`, JPEG quality `55`, MJPG, and `10` warmup frames because higher settings can show corrupt MJPG frames when USB bandwidth or power is limited.

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
- Dashboard redesign
- Multi-node live integration changes
- ESP32/LoRa hardware validation
