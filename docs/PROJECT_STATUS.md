# ADM FireNode Project Status

## Current Status
Repository is synchronized with GitHub main.

## Completed Validation
- Python tests passed
- Simulation smoke test passed
- PlatformIO 6.1.19 installed
- ESP32 sensor sender build passed
- ESP32 LoRa gateway build passed

## Next Incomplete Task
Run automated Raspberry Pi deployment from the MacBook in simulation mode, then validate Flask/API/stream placeholders on the four RPis.

## Immediate Goal
Deploy the Raspberry Pi web app to the four target RPis without requiring ESP32/LoRa hardware yet.

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
