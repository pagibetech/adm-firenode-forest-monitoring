# Source Artifacts

These artifacts informed the implementation workbook and baseline repository structure.

## Primary Artifacts

| Artifact | Workspace Path | Used For |
|---|---|---|
| Details-protoLORA.pdf | `Details-protoLORA.pdf` | LoRa objectives, validation tests, event algorithms, component options |
| FireDiagram.png | `FireDiagram.png` | Node topology, dashboard requirements, camera/siren notes |
| Main RPi v4 ZIP | `firenode_rpi_main_server_mlx90640_v4_2_three_nodes_simulation.zip` | Main server dashboard, MLX90640, multi-camera, simulation, chainsaw detector |
| Unified RPi v3 ZIP | `firenode_rpi_unified_system_v3_manual_start.zip` | Earlier node/main baseline reference |
| Zoom transcript/video | `/Users/macbookm1max321tb/A_Design/A_Company/1A_Students/ADM Lora Forest Fire/GMT20260331-121759_*` | Client decisions: LoRa for sensors, Wi-Fi for camera/dashboard, center main node |
| ESP32 v5 firmware | `ESP/FireNode_ESP32_v5/` | ESP32 sensor and LoRa sender baseline |

## Current Controlling Decisions

- Main server Raspberry Pi is physically installed on the center/backup field node.
- Remote nodes are Raspberry Pi + ESP32 because chainsaw/audio processing runs on the RPi.
- The existing RPi chainsaw detector is the baseline and should be improved rather than replaced immediately.
- All nodes, including the main server, have daytime cameras.
- Only the main server has the MLX90640 thermal camera.
- All nodes and the main server use 12V battery systems.
