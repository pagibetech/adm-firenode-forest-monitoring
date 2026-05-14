# ADM FireNode Forest Monitoring System

This repository is the implementation workspace for the ADM FireNode forest monitoring system.

The confirmed architecture is a four-node hybrid LoRa + Wi-Fi deployment:

- `node-main-center`: center/backup field node and main Raspberry Pi server.
- `node-01`, `node-02`, `node-03`: remote Raspberry Pi + ESP32 nodes.
- LoRa is the canonical path for sensor telemetry, alert packets, RSSI/SNR, and heartbeat data.
- Wi-Fi is used for camera feeds, dashboard viewing, setup, and diagnostics.
- Every node has a daytime camera.
- Only the main/center Raspberry Pi has the MLX90640 thermal camera.
- All nodes use 12V battery power with regulated 5V rails for Raspberry Pi hardware.

The workbook is the living project reference:

```text
docs/workbook/ADM_FireNode_Implementation_Workbook.xlsx
```

Update the workbook after every major completed step and commit it with the related code change.

## Repository Layout

```text
firmware/esp32-firenode/   ESP32 sensor sender PlatformIO firmware
firmware/esp32-lora-gateway/ ESP32 LoRa gateway PlatformIO firmware
raspi/firenode-system/       Raspberry Pi Flask dashboard/node baseline
simulation/                Simulation-first run notes and configs
scripts/                   Local helper scripts
docs/workbook/             Living implementation workbook
docs/artifacts/            Small reference summaries and generated docs
docs/deployment/           Field deployment checklist
docs/hardware/             Wiring and power references
docs/api/                  Packet and API contracts
```

## Fast Start

Run the local simulation smoke test:

```bash
./scripts/smoke_test_main_simulation.py
```

Or manually start the main dashboard simulation:

```bash
./scripts/start_main_simulation.sh
```

Then open:

```text
http://127.0.0.1:8090
```

## Current Build Path

1. Run the main RPi app in simulation mode.
2. Confirm the dashboard shows one main node and three simulated remote nodes.
3. Confirm all simulated sensor states, camera panels, chainsaw alerts, smoke alerts, and main thermal panel are visible.
4. Confirm `/api/lora/status`, `/api/lora/packets`, and `/api/recordings`.
5. Use that baseline before wiring real LoRa hardware.

See [simulation/README.md](simulation/README.md).

## Primary References

- [Living implementation workbook](docs/workbook/ADM_FireNode_Implementation_Workbook.xlsx)
- [Simulation guide](simulation/README.md)
- [Field deployment checklist](docs/deployment/field_deployment_checklist.md)
- [Hardware wiring reference](docs/hardware/wiring_reference.md)
- [LoRa packet and API schema](docs/api/lora_packet_schema.md)
- [Raspberry Pi app README](raspi/firenode-system/README.md)
- [ESP32 sensor sender firmware](firmware/esp32-firenode/README.md)
- [ESP32 LoRa gateway firmware](firmware/esp32-lora-gateway/README.md)
