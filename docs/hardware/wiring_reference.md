# FireNode Hardware Wiring Reference

This reference matches the current firmware defaults. Change firmware constants if the physical wiring changes.

## System Topology

- `main-center`: Raspberry Pi main server + daytime camera + MLX90640 (future) + ESP32 LoRa gateway + siren relay + 12 V battery.
- `node-01` to `node-03`: Raspberry Pi + ESP32 sensor sender + daytime camera + microphone + SX1278/Ra-02 LoRa sender + 12 V battery.
- Wi-Fi carries dashboard and camera streams.
- LoRa carries sensor telemetry and alert packets.
- MAIN ESP32 is physically connected to .51 RPi by USB serial at `/dev/ttyUSB0`; MAIN RPi reads sensor data via serial instead of HTTP API for local MAIN data and remote node packets forwarded by MAIN ESP32.

## ESP32 Sensor Sender Pins

Firmware path: `firmware/esp32-firenode/src/main.cpp`

| Function | ESP32 Pin | Notes |
|---|---|---:|
| DHT22 data | GPIO 27 | Use 10 kOhm pull-up to 3.3 V if sensor board lacks one |
| MQ2 digital output | GPIO 34 | Input-only pin; module must drive 3.3 V logic |
| PIR output | GPIO 32 | Assumes HIGH means motion |
| LoRa SCK | GPIO 18 | SX1278/Ra-02 SPI |
| LoRa MISO | GPIO 19 | SX1278/Ra-02 SPI |
| LoRa MOSI | GPIO 23 | SX1278/Ra-02 SPI |
| LoRa NSS/CS | GPIO 5 | SX1278/Ra-02 chip select |
| LoRa RST | GPIO 14 | SX1278/Ra-02 reset |
| LoRa DIO0 | GPIO 26 | SX1278/Ra-02 interrupt |

## ESP32 LoRa Gateway Pins (MAIN ESP32)

Firmware path: `firmware/esp32-lora-gateway/src/main.cpp`

| Function | ESP32 Pin | Notes |
|---|---|---:|
| LoRa SCK | GPIO 18 | SX1278/Ra-02 SPI |
| LoRa MISO | GPIO 19 | SX1278/Ra-02 SPI |
| LoRa MOSI | GPIO 23 | SX1278/Ra-02 SPI |
| LoRa NSS/CS | GPIO 5 | SX1278/Ra-02 chip select |
| LoRa RST | GPIO 14 | SX1278/Ra-02 reset |
| LoRa DIO0 | GPIO 26 | SX1278/Ra-02 interrupt |
| USB serial | ESP32 USB | Raspberry Pi reads `/dev/ttyUSB0` at 115200 baud |

## Raspberry Pi Main Node (.51)

| Device | Connection | Notes |
|---|---|---|
| Daytime camera | CSI (Raspberry Pi Camera Rev 1.3) | Official hardware: ov5647 via CSI ribbon; deprecated USB webcam path |
| MLX90640 | I2C | Default address `0x33`; enable I2C on Raspberry Pi. **Not yet installed; preserved as future MAIN-only hardware.** |
| ESP32 LoRa gateway | USB serial | MAIN ESP32 connected by USB at `/dev/ttyUSB0`, 115200 baud. `modules/esp32_serial_reader.py` reads sensor data directly from serial. |
| Siren relay | GPIO TBD | Keep relay driver isolated; confirm pin before enabling live siren control |
| 12 V battery | Fused input to buck converter | Use stable 5 V converter for Raspberry Pi |

## Raspberry Pi Remote Node

| Device | Connection | Notes |
|---|---|---|
| Daytime camera | CSI (Raspberry Pi Camera Rev 1.3) | Official hardware: ov5647 via CSI ribbon; stream shown on main dashboard over Wi-Fi |
| Microphone | USB preferred | Existing chainsaw detector uses Raspberry Pi audio path; not yet installed |
| ESP32 sensor sender | LoRa (via ESP32 firmware) | Sensor telemetry sent over LoRa by ESP32 firmware to MAIN ESP32 |
| 12 V battery | Fused input to buck converter | Use stable 5 V converter for Raspberry Pi |

## Power Notes

- Use one fused 12 V input per field unit.
- Use a 5 V buck converter rated for Raspberry Pi peak load.
- Power the SX1278/Ra-02 from 3.3 V only.
- If an MQ2 module is powered from 5 V, level-shift or divide its digital output before ESP32 GPIO.
- Add battery voltage telemetry with a divider sized for ESP32 ADC input range before field runtime testing.

## LoRa Defaults

| Setting | Value |
|---|---:|
| Frequency | 433 MHz |
| Spreading factor | 7 |
| Bandwidth | 125 kHz |
| Coding rate denominator | 5 |
| Sync word | `0x12` |
| Sender TX power | 17 dBm |

## ESP32 Bench Validation Notes (2026-06-02)

- MAIN and NODE_01 ESP32 bench validation PASSED.
- LoRa two-way communication confirmed between MAIN and NODE_01 (RSSI -29 to -35 dBm; SNR 9.25 to 10.00).
- DHT22, PIR, MQ analog, and LoRa TX/RX are working on MAIN and NODE_01.
- Battery ADC on MAIN appears floating/unconnected — verify voltage divider wiring and ADC pin assignment before field runtime.
- NODE_02 and NODE_03 ESP32 hardware are not yet available/assembled; expected same wiring/firmware as NODE_01.

## MAIN ESP32 USB Serial Notes (2026-06-08)

- MAIN ESP32 is physically connected to .51 RPi by USB serial at `/dev/ttyUSB0`.
- Baud rate: 115200 (matches ESP32 firmware default).
- Minicom confirmed readable serial data from MAIN ESP32.
- MAIN ESP32 receives LoRa packets from NODE_01 and outputs them over USB serial.
- Example received packet:
  ```
  [RECEIVED] NODE=NODE_01,SEQ=1765,TEMP=27.20,HUM=63.20,PIR=0,MQ=2095,BAT=2926
  ```
- Example MAIN local packet:
  ```
  [LORA TX OK] NODE=MAIN,SEQ=1765,TEMP=27.70,HUM=62.90,PIR=0,MQ=356,BAT=0
  ```
- `modules/esp32_serial_reader.py` parses these lines and feeds dashboard sensor cards.
- HTTP ESP32 fallback is preserved when serial is disabled or unavailable.

## Camera Hardware Decision (Updated 2026-06-02)

- USB webcam is deprecated/removed from target design.
- Official camera hardware: Raspberry Pi Camera Rev 1.3 (ov5647) via CSI ribbon.
- Detection command: `rpicam-hello --list-cameras`
- Detected sensor: `ov5647 [2592x1944 10-bit GBRG]`
- Detected modes:
  - 640x480 @ 58.92 fps
  - 1296x972 @ 46.34 fps
  - 1920x1080 @ 32.81 fps
  - 2592x1944 @ 15.63 fps
- .51 MAIN and .52 NODE_01: detection confirmed.
- .53 NODE_02 and .54 NODE_03: target hardware installed; pending physical confirmation.
- Implementation direction: rpicam/libcamera-based capture pipeline for production; OpenCV USB path kept only as fallback reference.

## Thermal Camera Notes

- MLX90640 thermal camera is **MAIN ONLY** and is part of the architecture.
- **Not yet physically installed** on .51 but preserved; no removal.
- Default I2C address `0x33`; enable I2C on Raspberry Pi.
- Will be used for 360-degree thermal scan with servo in future milestone.

## Open Hardware Decisions

- Siren relay GPIO pin is still intentionally unassigned.
- Battery chemistry and Ah rating are still needed for runtime and low-voltage thresholds.
- USB microphone is not installed yet and will be used later for chainsaw detection only.
- NODE_02 and NODE_03 hardware builds are pending.
