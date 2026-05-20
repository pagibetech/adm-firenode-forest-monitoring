# ADM FireNode Active Context

Project: ADM FireNode Forest Monitoring System

Repo:
https://github.com/pagibetech/adm-firenode-forest-monitoring

Current synchronized branch:
main

Current known validation state:
- Python tests passed
- Simulation smoke test passed
- PlatformIO installed: 6.1.19
- ESP32 sensor sender build passed
- ESP32 LoRa gateway build passed

Current next incomplete milestone:
Automated Raspberry Pi deployment phase in simulation mode

Current operating rule:
Continue only from the next incomplete task. Do not start new architecture work until workflow memory, workbook, and status files are updated.

Current deployment targets:
- 192.168.9.51 = Main Server
- 192.168.9.52 = Node 1
- 192.168.9.53 = Node 2
- 192.168.9.54 = Node 3

Current deployment mode:
- MacBook-run SSH deployment using key `~/admfire`
- SSH user `betech`
- ESP32/LoRa hardware validation paused
- Raspberry Pi app deployed in simulation mode

Latest completed task:
- Updated automated RPi deployment scripts for parallel default deployment, sequential mode, single-target mode, per-RPi logs, pass/fail summary, and deployment-role config labels.
- Main server deployment is successful and dashboard/API are working on `192.168.9.51`.
- Added live USB camera MJPG/V4L2 capture support after `/dev/video0` opened but default OpenCV reads failed.
- Lowered RPi 3B USB camera defaults to `320x240`, `10 FPS`, JPEG quality `55`, MJPG, and `10` warmup frames after corrupt MJPG frame warnings.

Next exact command:
- Deploy the camera fix to the main server only: `./scripts/deploy_all_rpis.sh --target 192.168.9.51 --skip-setup`
