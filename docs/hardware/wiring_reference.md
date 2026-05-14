# FireNode Hardware Wiring Reference

This reference matches the current firmware defaults. Change firmware constants if the physical wiring changes.

## System Topology

- `main-center`: Raspberry Pi main server + daytime camera + MLX90640 + ESP32 LoRa gateway + siren relay + 12 V battery.
- `node-01` to `node-03`: Raspberry Pi + ESP32 sensor sender + daytime camera + microphone + SX1278/Ra-02 LoRa sender + 12 V battery.
- Wi-Fi carries dashboard and camera streams.
- LoRa carries sensor telemetry and alert packets.

## ESP32 Sensor Sender Pins

Firmware path: `firmware/esp32-firenode/src/main.cpp`

| Function | ESP32 Pin | Notes |
|---|---:|---|
| DHT22 data | GPIO 27 | Use 10 kOhm pull-up to 3.3 V if sensor board lacks one |
| MQ2 digital output | GPIO 34 | Input-only pin; module must drive 3.3 V logic |
| PIR output | GPIO 32 | Assumes HIGH means motion |
| LoRa SCK | GPIO 18 | SX1278/Ra-02 SPI |
| LoRa MISO | GPIO 19 | SX1278/Ra-02 SPI |
| LoRa MOSI | GPIO 23 | SX1278/Ra-02 SPI |
| LoRa NSS/CS | GPIO 5 | SX1278/Ra-02 chip select |
| LoRa RST | GPIO 14 | SX1278/Ra-02 reset |
| LoRa DIO0 | GPIO 26 | SX1278/Ra-02 interrupt |

## ESP32 LoRa Gateway Pins

Firmware path: `firmware/esp32-lora-gateway/src/main.cpp`

| Function | ESP32 Pin | Notes |
|---|---:|---|
| LoRa SCK | GPIO 18 | SX1278/Ra-02 SPI |
| LoRa MISO | GPIO 19 | SX1278/Ra-02 SPI |
| LoRa MOSI | GPIO 23 | SX1278/Ra-02 SPI |
| LoRa NSS/CS | GPIO 5 | SX1278/Ra-02 chip select |
| LoRa RST | GPIO 14 | SX1278/Ra-02 reset |
| LoRa DIO0 | GPIO 26 | SX1278/Ra-02 interrupt |
| USB serial | ESP32 USB | Raspberry Pi reads `/dev/ttyUSB0` or `/dev/ttyACM0` |

## Raspberry Pi Main Node

| Device | Connection | Notes |
|---|---|---|
| Daytime camera | USB or CSI | Simulation fallback works without camera; live field mode needs hardware |
| MLX90640 | I2C | Default address `0x33`; enable I2C on Raspberry Pi |
| ESP32 LoRa gateway | USB serial | Run `install_lora_gateway_service.sh` after confirming device path |
| Siren relay | GPIO TBD | Keep relay driver isolated; confirm pin before enabling live siren control |
| 12 V battery | Fused input to buck converter | Use stable 5 V converter for Raspberry Pi |

## Raspberry Pi Remote Node

| Device | Connection | Notes |
|---|---|---|
| Daytime camera | USB or CSI | Stream shown on main dashboard over Wi-Fi |
| Microphone | USB preferred | Existing chainsaw detector uses Raspberry Pi audio path |
| ESP32 sensor sender | Wi-Fi and/or USB | Sensor telemetry sent over LoRa by ESP32 firmware |
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

## Open Hardware Decisions

- Siren relay GPIO pin is still intentionally unassigned.
- Battery chemistry and Ah rating are still needed for runtime and low-voltage thresholds.
- Final camera type per node, USB vs CSI vs fisheye, can be chosen during bench testing.
