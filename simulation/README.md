# FireNode Simulation Baseline

Simulation is the first implementation stage. It proves the dashboard, four-node topology, camera panels, thermal panel, alert states, and data flow before hardware variables such as LoRa wiring, microphones, cameras, and battery rails are introduced.

## What Simulation Represents

| Simulated Unit | Real Target |
|---|---|
| Local main server | Center/backup field Raspberry Pi with dashboard, daytime camera, MLX90640, LoRa receiver, siren control |
| Remote node 1 | RPi + ESP32 + LoRa + daytime camera + mic + DHT/MQ2 |
| Remote node 2 | RPi + ESP32 + LoRa + daytime camera + mic + DHT/MQ2 |
| Remote node 3 | RPi + ESP32 + LoRa + daytime camera + mic + DHT/MQ2 |

## Run Main Dashboard Simulation

From the repository root:

```bash
./scripts/start_main_simulation.sh
```

Then open:

```text
http://127.0.0.1:8090
```

On a Raspberry Pi or LAN device, open:

```text
http://<main-rpi-ip>:8090
```

## Expected Result

- Dashboard opens on port `8090`.
- Role is `server`.
- Operation mode is `simulation`.
- Three remote node slots are visible.
- Local thermal stream is visible as simulated MLX90640 output if physical MLX90640 is absent.
- Local main camera stream works in simulation mode even if OpenCV or USB camera hardware is absent.
- `/api/lora/status` reports four active simulated LoRa nodes: main/center plus remote slots 1-3.
- `/api/lora/packets` returns the SQLite-backed packet history that the real receiver path will reuse.
- `/api/lora/ingest` accepts a JSON packet for future serial/SPI gateway adapters and stores it using the same schema.
- Each simulated LoRa packet includes `packet_id`, `seq`, `rssi_dbm`, `snr_db`, `pdr_estimate_pct`, frequency/settings, battery voltage, and alert flags.
- Simulated smoke, chainsaw, and thermal events appear in the alert table.
- Camera panels use simulated/placeholder feeds until real node cameras are attached.

## Exit Criteria for Phase 1 Simulation

- Main dashboard displays all four node positions.
- Sensor update cadence and event display are understandable.
- The workbook `Progress Tracker`, `Issue Log`, and `Change Log` are updated.
- Next implementation task is selected from the workbook.

## Next Hardware Step After Simulation

Once dashboard and packet simulation are accepted, wire one LoRa pair and replace the simulator with the real receiver:

```text
remote node telemetry packet -> main LoRa gateway receiver -> SQLite reading/event store -> dashboard
```

The first hardware adapter is prepared as a serial bridge:

```bash
cd raspi/firenode-system
python3 lora_gateway_serial.py --port /dev/ttyUSB0 --baud 115200 --api-base http://127.0.0.1:8090
```

It expects one JSON LoRa packet per serial line from an ESP32/SX127x gateway and posts each packet to `/api/lora/ingest`.
