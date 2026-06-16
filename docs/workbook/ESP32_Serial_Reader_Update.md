# ESP32 Serial Reader Integration Update

Date: 2026-06-02 / 2026-06-08 / 2026-06-10
Task: Integrate ESP32 serial data into RPi dashboards (MAIN + NODE).
Status: **IMPLEMENTED / NODE LOCAL SERIAL ADDED / VERIFICATION PENDING**

## 2026-06-10 Update: NODE Local ESP32 Serial/UART Status
- NODE RPis now start the serial reader on `/dev/ttyUSB0` (GPIO UART) when role is "node".
- `config.json` key added: `esp32_serial_port` (default: "/dev/ttyUSB0").
- `get_local_node_data()` for node roles: first checks local serial cache for non-MAIN node IDs; falls back to HTTP ESP32 if no serial data.
- `/api/status` now exposes `local_serial` object with: enabled, connected, port, error, last_packet_time, packets_by_node, cache_keys.
- NODE dashboard (node_dashboard.html + node_app.js): ESP32 Local Serial card with green/yellow/red indicator.
- NODE sensor readings prefer local serial cache; show "Waiting for data" placeholder when no packets received.
- No ESP32 firmware changes. MAIN dashboard behavior preserved.
- No "Scan ESP32 and Select" required for local NODE serial data.
- py_compile all modules PASS.

## Files Created
- `raspi/firenode-system/modules/esp32_serial_reader.py`
  - Thread-safe serial reader using pyserial.
  - Parses lines containing `NODE=...` and caches latest per node ID.
  - Ignores decorative lines (`===== LORA RX =====`, `[RSSI]`, `[SNR]`, etc.).
  - Exposes `get_cache()`, `get_status()`, and helper conversion functions.

## Files Modified
- `raspi/firenode-system/config.json`
  - Added keys:
    - `esp32_serial_enabled` (default: true)
    - `esp32_serial_port` (default: "/dev/ttyUSB0")
    - `esp32_serial_baud` (default: 115200)
- `raspi/firenode-system/app.py`
  - Imports `ESP32SerialReader`, `serial_data_to_esp32_format`, `sensor_summary_from_serial`.
  - Added `esp32_serial_reader` global instance.
  - `DEFAULT_CONFIG` updated with serial settings.
  - `get_local_node_data()` now checks serial cache for `MAIN` before falling back to HTTP ESP32 fetch.
  - `build_remote_slots()` overlays serial data for remote nodes (slots 1-3 mapped to `NODE_01`, `NODE_02`, `NODE_03`).
  - `_overlay_serial_remote_node()` converts placeholder nodes to online when serial data exists.
  - `/api/status` now includes `serial` field with `serial_connected`, `serial_error`, `last_packet_time`, `packets_by_node`.
  - `/api/config` POST allows updating `esp32_serial_enabled`, `esp32_serial_port`, `esp32_serial_baud`.
  - `main()` starts the serial reader when `esp32_serial_enabled` is true and role is `server`.
- `docs/ACTIVE_CONTEXT.md`
  - Added section documenting serial reader integration.
- `docs/PROJECT_STATUS.md`
  - Added ESP32 Serial Reader Implementation section.
- `docs/AI_SESSION_HANDOFF.md`
  - Updated with serial reader status and pending validation steps.
- `docs/hardware/wiring_reference.md`
  - Added MAIN ESP32 USB Serial Notes section.
- `docs/deployment/field_deployment_checklist.md`
  - Added ESP32 Serial Reader Validation section (Step 6).

## Hardware Context
- MAIN ESP32 is physically connected to .51 RPi by USB serial at `/dev/ttyUSB0`.
- Minicom confirmed readable serial data at 115200 baud.
- MAIN ESP32 receives LoRa packets from NODE_01.
- Example received packet:
  ```
  [RECEIVED] NODE=NODE_01,SEQ=1765,TEMP=27.20,HUM=63.20,PIR=0,MQ=2095,BAT=2926
  ```
- Example MAIN local packet:
  ```
  [LORA TX OK] NODE=MAIN,SEQ=1765,TEMP=27.70,HUM=62.90,PIR=0,MQ=356,BAT=0
  ```

## Parsing Logic Summary
1. Read raw line from `/dev/ttyUSB0` at 115200.
2. Decode UTF-8, strip whitespace.
3. If line does not contain `NODE=`, ignore it.
4. Extract substring starting at `NODE=`.
5. Split by comma, then split each part by `=` into key/value.
6. Map keys:
   - `NODE` → `node_id`
   - `SEQ` → `seq`
   - `TEMP` → `temperature`
   - `HUM` → `humidity`
   - `PIR` → `pir`
   - `MQ` → `mq`
   - `BAT` → `bat`
7. If `node_id` is missing, discard.
8. Store in thread-safe cache dict keyed by `node_id`.
9. Update counters and `last_packet_time`.

## Dashboard Mapping Summary
- **NODE=MAIN** → Local node (`FireNode-192-168-9-51`) sensor card on MAIN dashboard.
- **NODE=NODE_01** → Remote slot 1 (`FireNode-192-168-9-52`) sensor card on MAIN dashboard.
- **NODE=NODE_02** → Remote slot 2 (`FireNode-192-168-9-53`) sensor card — pending hardware build.
- **NODE=NODE_03** → Remote slot 3 (`FireNode-192-168-9-54`) sensor card — pending hardware build.
- **NODE local serial** (.52/.53/.54): Each NODE RPi shows its paired ESP32 data from local UART (/dev/ttyUSB0) on the NODE dashboard.
- Nodes without serial data remain placeholders (offline) unless pulled via HTTP.
- HTTP fallback for ESP32 data is preserved when serial is disabled or no data exists.

## Validation Performed
- `python3 -m py_compile` passed for `app.py` and `esp32_serial_reader.py`.
- `config.json` JSON syntax validated.
- Parsing unit test passed (verified `NODE=MAIN` and `NODE=NODE_01` lines, ignored decorative lines).
- No changes to CSI camera, thermal camera, or ESP32 firmware.

## Pending Verification
- [ ] Confirm `/dev/ttyUSB0` exists and minicom shows readable output on .51 (MAIN).
- [x] Confirm `/dev/ttyUSB0` exists on .54 (NODE03 — VERIFIED 2026-06-12).
- [ ] Confirm `/dev/ttyUSB0` exists on .52/.53 (NODE01/NODE02 — not yet checked).
- [x] Confirm `/api/status` shows `local_serial.connected: true` on .54 (VERIFIED).
- [x] Confirm NODE dashboard ESP32 Local Serial card works on .54 (VERIFIED — yellow "Waiting for UART data").
- [ ] Confirm NODE sensor readings populate from local serial cache (pending ESP32 UART wiring).
- [ ] Confirm `/api/status` shows `local_serial` on .51 (blocked: .51 unavailable).
- [ ] Confirm `/api/server-dashboard` sensor cards populate from serial data on .51.
- [ ] Confirm NODE_01 camera is visible on MAIN dashboard in LIVE mode.
- [ ] Confirm NODE_01 remote slot 1 shows data when LoRa packets are received.
- [ ] Confirm NODE_02 and NODE_03 remain placeholders (offline) on MAIN dashboard.
- [ ] Confirm HTTP ESP32 fallback works when serial is disabled.

## Suggested Commit Message
```
feat(serial): integrate MAIN ESP32 USB serial into dashboard

- Add modules/esp32_serial_reader.py for /dev/ttyUSB0 115200 reads
- Parse NODE=MAIN and NODE=NODE_01 packets; cache per node ID
- Overlay serial data into local and remote node slots in live mode
- Add config keys: esp32_serial_enabled, esp32_serial_port, esp32_serial_baud
- Expose serial status via /api/status
- Preserve HTTP ESP32 fallback; no camera/thermal/firmware changes
- Update docs: ACTIVE_CONTEXT, PROJECT_STATUS, AI_SESSION_HANDOFF,
  wiring_reference, field_deployment_checklist, workbook
```
