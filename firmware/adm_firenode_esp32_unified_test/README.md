# ADM FireNode ESP32 Unified Wiring + LoRa Test

Use this PlatformIO project to test every ESP32 unit in the ADM FireNode system.

The same program can be uploaded to:

- MAIN ESP32
- NODE_01 ESP32
- NODE_02 ESP32
- NODE_03 ESP32

Only change the `NODE_ID` value in `src/main.cpp` before uploading to each board.

```cpp
#define NODE_ID "NODE_01"
```

Recommended IDs:

```cpp
#define NODE_ID "MAIN"
#define NODE_ID "NODE_01"
#define NODE_ID "NODE_02"
#define NODE_ID "NODE_03"
```

## Pinout

### Sensors

| Device | ESP32 Pin |
|---|---|
| DHT22 Data | GPIO 4 |
| PIR OUT | GPIO 27 |
| MQ Smoke Analog | GPIO 34 |
| Battery Voltage Sense | GPIO 35 |
| Status LED | GPIO 2 |

### SX1278 / RA-02 LoRa

| LoRa Pin | ESP32 Pin |
|---|---|
| VCC | 3.3V only |
| GND | GND |
| SCK | GPIO 18 |
| MISO | GPIO 19 |
| MOSI | GPIO 23 |
| NSS / CS | GPIO 5 |
| RESET | GPIO 14 |
| DIO0 | GPIO 26 |

## Important Notes

- RA-02/SX1278 is 3.3V only.
- Do not connect 5V to the LoRa module.
- Always attach a 433 MHz antenna before LoRa transmission.
- MQ module analog output may exceed 3.3V. Use a voltage divider if needed.
- DHT22 data line should have a 10k pull-up resistor to 3.3V.

## How to Use in VS Code + PlatformIO

1. Extract the ZIP file.
2. Open the folder in VS Code.
3. Install PlatformIO extension if not yet installed.
4. Open `src/main.cpp`.
5. Set the correct `NODE_ID`.
6. Connect ESP32 by USB.
7. Click PlatformIO Upload.
8. Open Serial Monitor at `115200` baud.

## Expected Serial Monitor Output

You should see:

```text
[PASS] LoRa initialized at 433 MHz.
[PASS] DHT22: 30.50 C / 75.00 %
[INFO] PIR GPIO27: LOW / No motion
[INFO] MQ GPIO34 Raw: 1234
[INFO] Battery GPIO35 Raw: 2048
[LORA TX OK] NODE=NODE_01,SEQ=0,...
```

If another ESP32 is powered and running this same program, you should also see:

```text
========== LORA RX ==========
[RECEIVED] NODE=MAIN,SEQ=0,...
[RSSI] -55
[SNR] 9.75
=============================
```

## Test Procedure

1. Upload the program to the MAIN ESP32 with `NODE_ID "MAIN"`.
2. Upload the program to NODE_01 with `NODE_ID "NODE_01"`.
3. Open Serial Monitor for at least one board.
4. Confirm both TX and RX messages appear.
5. Repeat for NODE_02 and NODE_03.

## Troubleshooting

### LoRa init failed

Check:

- LoRa VCC is 3.3V, not 5V
- GND is common with ESP32
- SCK = GPIO18
- MISO = GPIO19
- MOSI = GPIO23
- NSS/CS = GPIO5
- RESET = GPIO14
- DIO0 = GPIO26
- Antenna connected

### DHT22 failed

Check:

- DATA = GPIO4
- VCC = 3.3V
- GND = GND
- 10k pull-up resistor from DATA to 3.3V

### MQ reading too high

Check that AOUT does not exceed 3.3V before connecting to ESP32 GPIO34.

### PIR always high or low

Check PIR power and warm-up time. Many PIR modules need 30-60 seconds after power-up.
