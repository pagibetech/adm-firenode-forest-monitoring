# ADM FireNode AI Session Handoff

## Handoff Summary
The project has passed local software and firmware build validation. Codex 5-hour limit is exhausted, so use VS Code + Roo Code + Kimi for small/medium tasks only.

## Next Task
Run Raspberry Pi automated deployment in simulation mode from the MacBook.

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
Use the new deployment scripts to deploy/update the Raspberry Pi app before resuming hardware validation. ESP32/LoRa hardware validation is paused.

## Latest Implementation Added
- `scripts/deploy_main_server.sh`
- `scripts/deploy_node.sh`
- `scripts/deploy_all_rpis.sh`
- `docs/deployment/rpi_automated_deployment.md`

## Expected Validation
- `bash -n` on all deployment scripts.
- `./scripts/deploy_all_rpis.sh` from the MacBook when RPis are reachable.
- Manual start on each RPi with `/home/betech/admfire/raspi/firenode-system/run.sh`.
- API checks against `/api/status`, `/api/config`, `/api/node-data`, `/api/server-dashboard`, and `/api/lora/status`.
- Stream placeholder checks against `/video_feed` and main `/thermal.png`.
