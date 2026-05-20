# ADM FireNode Architecture

Confirmed architecture:
- Four-node hybrid LoRa + Wi-Fi deployment
- node-main-center: center/backup field node and main Raspberry Pi server
- node-01, node-02, node-03: remote Raspberry Pi + ESP32 nodes
- LoRa is canonical path for sensor telemetry, alert packets, RSSI/SNR, and heartbeat data
- Wi-Fi is used for camera feeds, dashboard viewing, setup, and diagnostics
- Every node has a daytime camera
- Only the main/center Raspberry Pi has the MLX90640 thermal camera
