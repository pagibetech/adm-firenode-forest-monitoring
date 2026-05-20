# ADM FireNode AI Session Handoff

## Handoff Summary
The project has passed local software and firmware build validation. Codex 5-hour limit is exhausted, so use VS Code + Roo Code + Kimi for small/medium tasks only.

## Next Task
Deploy and validate the main server USB camera MJPG/V4L2 fix.

## Required First Checks
Before editing, inspect:
- docs/ACTIVE_CONTEXT.md
- docs/PROJECT_STATUS.md
- docs/AI_SESSION_HANDOFF.md
- docs/CODEX_RULES.md
- docs/AI_ROUTING_RULES.md
- docs/CODEX_LIMIT_STATUS.md
- docs/workbook/ADM_FireNode_Implementation_Workbook.xlsx

## Current Instruction
Main server is deployed successfully at `192.168.9.51`; dashboard/API are working. Fix the live USB camera path only. ESP32/LoRa hardware validation remains paused.

## Latest Implementation Added
- `scripts/deploy_main_server.sh`
- `scripts/deploy_node.sh`
- `scripts/deploy_all_rpis.sh`
- `docs/deployment/rpi_automated_deployment.md`
- `deploy_all_rpis.sh` now supports parallel default deployment, `--sequential`, `--target <ip>`, per-IP logs, and final pass/fail summary.
- RPi app config now accepts deployment role aliases: `main_server`, `node_01`, `node_02`, `node_03`.

## Expected Validation
- `bash -n` on all deployment scripts.
- `./scripts/deploy_all_rpis.sh` from the MacBook when RPis are reachable.
- Manual start on each RPi with `/home/betech/admfire/raspi/firenode-system/run.sh`.
- API checks against `/api/status`, `/api/config`, `/api/node-data`, `/api/server-dashboard`, and `/api/lora/status`.
- Stream placeholder checks against `/video_feed` and main `/thermal.png`.
- Main server camera test: `./venv/bin/python camera_test.py --device 0 --fourcc MJPG --width 640 --height 480 --fps 25`.
- Dashboard camera route: `curl -I --max-time 5 http://192.168.9.51:8090/video_feed`.

## Next Exact Command

```bash
cd "/Users/macbookm1max321tb/A_Design/A_Coding/ADM Fire"
./scripts/deploy_all_rpis.sh --target 192.168.9.51 --skip-setup
```
