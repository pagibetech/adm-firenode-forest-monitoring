#!/usr/bin/env python3
"""Update the ADM FireNode workbook to reflect current project status as of 2026-06-08."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font
except Exception as exc:
    print(f"ERROR: openpyxl is required: {exc}", file=sys.stderr)
    raise SystemExit(1)

WORKBOOK = Path(__file__).resolve().parents[1] / "docs" / "workbook" / "ADM_FireNode_Implementation_Workbook.xlsx"
DATE_STR = "2026-06-08"


def update_dashboard(wb):
    ws = wb["Dashboard"]
    # Row 9 = Current Stage (from earlier inspection it was row 9, but serial script targeted B10)
    # Based on inspection: row 9 = Current Stage, row 10 = Next Action, row 11 = extra next action text
    ws["B9"] = (
        "MAIN .51 dashboard is in LIVE mode. "
        "MAIN .51 CSI camera works. "
        "NODE_01 .52 CSI camera works and appears on MAIN dashboard. "
        "MAIN can discover/pull NODE_01 data. "
        "Remote node aggregation is working for .52. "
        ".53 and .54 are pending hardware build. "
        "Thermal camera is part of MAIN design but not physically installed yet. "
        "USB microphone/chainsaw detection is still pending. "
        "MAIN ESP32 USB serial integration has been implemented in code but is pending deployment/verification. "
        "MAIN ESP32 serial data was manually confirmed by Minicom on /dev/ttyUSB0 at 115200."
    )
    ws["B10"] = (
        "Next: Deploy updated raspi/firenode-system to .51 MAIN and validate live mode sensor cards from serial. "
        "Confirm NODE_01 camera remains visible on MAIN dashboard after redeploy. "
        "Assemble and validate .53/.54 hardware when available. "
        "Install thermal camera on MAIN when hardware arrives. "
        "Install USB microphone and validate chainsaw detection pipeline."
    )
    ws["B11"] = None


def update_progress_tracker(wb):
    ws = wb["Progress Tracker"]
    max_row = ws.max_row
    new_rows = [
        [
            "P054", "Hardware", "CSI camera validation .51 PASS",
            "Done", "User/Codex", DATE_STR,
            "MAIN .51 dashboard in LIVE mode; CSI camera feed confirmed",
            "Validate .52 NODE_01 camera feed on MAIN dashboard"
        ],
        [
            "P055", "Hardware", "CSI camera validation .52 PASS",
            "Done", "User/Codex", DATE_STR,
            "NODE_01 .52 CSI camera works and appears on MAIN dashboard",
            "Validate remote node aggregation from .52 to .51"
        ],
        [
            "P056", "Integration", "Remote node aggregation .51 to .52 PASS",
            "Done", "User/Codex", DATE_STR,
            "MAIN can discover/pull NODE_01 data; remote slot 1 populated",
            "Validate ESP32 serial reader deployment on .51"
        ],
        [
            "P057", "Integration", "MAIN ESP32 USB serial reader IMPLEMENTED / PENDING VERIFICATION",
            "In Progress", "Codex", DATE_STR,
            "modules/esp32_serial_reader.py created; app.py/config updated; py_compile passed; manual Minicom confirmed /dev/ttyUSB0 at 115200",
            "Deploy to .51 MAIN and validate live serial sensor cards"
        ],
        [
            "P058", "Hardware", "MAIN ESP32 serial hardware manually confirmed using Minicom",
            "Done", "User", DATE_STR,
            "Serial packet examples: NODE=MAIN,SEQ=1765,TEMP=27.70,HUM=62.90,PIR=0,MQ=356,BAT=0; NODE=NODE_01,SEQ=1765,TEMP=27.20,HUM=63.20,PIR=0,MQ=2095,BAT=2926",
            "Deploy serial reader code and confirm dashboard integration"
        ],
        [
            "P059", "Hardware", ".53 NODE_02 and .54 NODE_03 pending hardware build",
            "Not Started", "User", DATE_STR,
            "CSI cameras installed; ESP32 hardware not yet assembled; no power/LoRa validation possible",
            "Assemble NODE_02/NODE_03 ESP32 + LoRa + sensor wiring and validate with NODE_01 baseline"
        ],
        [
            "P060", "Hardware", "Thermal camera pending installation, but retained as MAIN-only design component",
            "Not Started", "User/Codex", DATE_STR,
            "MLX90640 is in BOM and design; not physically installed on MAIN yet",
            "Install thermal camera on MAIN and validate /thermal_feed endpoint"
        ],
        [
            "P061", "Audio", "Chainsaw detection pending USB microphone installation/testing",
            "Not Started", "User/Codex", DATE_STR,
            "detector.py baseline exists; no USB microphone connected to any node for live validation",
            "Install USB microphone on a node, run detector.py, and validate chainsaw alert + recording"
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_issue_log(wb):
    ws = wb["Issue Log"]
    max_row = ws.max_row
    # Ensure historical USB webcam issue remains documented (I012)
    # Add new issues
    new_rows = [
        [
            "I017", "Integration", "MAIN ESP32 USB serial reader implemented but not yet deployed/verified on .51 MAIN",
            "Dashboard sensor cards may still use HTTP fallback until serial is validated in live mode",
            "Codex", "Open",
            "Deploy updated raspi/firenode-system to .51 and verify /api/status serial_connected=true and sensor cards populate from serial cache.",
        ],
        [
            "I018", "Hardware", ".53 NODE_02 and .54 NODE_03 hardware build pending",
            "Cannot validate full 4-node LoRa mesh or camera grid until ESP32 + sensors + LoRa are assembled",
            "User", "Open",
            "Assemble NODE_02/NODE_03 using NODE_01 wiring/firmware baseline; run rpicam-hello and LoRa bench test.",
        ],
        [
            "I019", "Hardware", "Thermal camera (MLX90640) not yet physically installed on MAIN",
            "Thermal night detection feature unavailable until hardware is mounted and wired",
            "User", "Open",
            "Install MLX90640 on MAIN RPi I2C and validate /thermal_feed endpoint.",
        ],
        [
            "I020", "Audio", "USB microphone not installed on any node; chainsaw detection pipeline untested",
            "Audio alert and event recording features cannot be validated in live mode",
            "User/Codex", "Open",
            "Install USB microphone on a node, run detector.py with field audio or synthetic test clips, validate score threshold and recording trigger.",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_decision_log(wb):
    ws = wb["Decision Log"]
    max_row = ws.max_row
    new_rows = [
        [
            "D010", DATE_STR,
            "MAIN .51 dashboard operates in LIVE mode with CSI camera and ESP32 serial integration",
            ".51 is the field main server; simulation mode is no longer the primary runtime; CSI camera provides stable daytime feed; serial provides local ESP32 data",
            "Dashboard validation on .51; rpicam-hello and minicom confirmations",
            "LIVE mode is the default for .51; simulation remains available for local development.",
        ],
        [
            "D011", DATE_STR,
            ".53 and .54 remain in pending hardware state; no remote ESP32 assembly yet",
            "CSI cameras are installed but ESP32 + LoRa + sensor wiring is not assembled; cannot proceed with node validation",
            "Hardware inventory status",
            "NODE_02/NODE_03 assembly is the next hardware milestone after MAIN/NODE_01 are fully validated.",
        ],
        [
            "D012", DATE_STR,
            "Thermal camera and USB microphone are retained in design but deferred until hardware is available",
            "MLX90640 and USB mic are in BOM and code; field validation blocked by physical installation",
            "Design documents and code baseline already include thermal and audio modules",
            "Install thermal on MAIN first; install USB mic on one node for chainsaw validation.",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_build_validation_matrix(wb):
    ws = wb["Build Validation Matrix"]
    max_row = ws.max_row
    new_rows = [
        [
            "CSI camera validation .51",
            "N/A (hardware)",
            "Pass on .51",
            "Pass",
            "MAIN .51 dashboard LIVE mode; CSI feed clear and stable",
            "Visual inspection on dashboard; rpicam-hello --list-cameras; curl /video_feed",
            "None.",
        ],
        [
            "CSI camera validation .52",
            "N/A (hardware)",
            "Pass on .52",
            "Pass",
            "NODE_01 .52 CSI feed visible on MAIN dashboard",
            "Visual inspection on MAIN dashboard remote camera grid; rpicam-hello on .52",
            "None.",
        ],
        [
            "Remote node aggregation .51 to .52",
            "Pass local compile/tests",
            "Pass on .51/.52 network",
            "Pass",
            "MAIN discovers NODE_01; remote slot 1 populated with sensor and camera data",
            "Dashboard inspection; /api/server-dashboard JSON verification",
            "None for .52; .53/.54 pending hardware.",
        ],
        [
            "MAIN ESP32 USB serial reader",
            "Pass local compile/tests",
            "Pending hardware validation on .51",
            "In Progress",
            "modules/esp32_serial_reader.py; parsing unit test passed; py_compile passed; minicom confirmed hardware output",
            "python3 -m py_compile; manual parse_line test; minicom on /dev/ttyUSB0 115200",
            "Dashboard sensor overlay not yet verified in live mode; HTTP fallback preserved.",
        ],
        [
            "MAIN ESP32 serial hardware confirmation",
            "N/A (hardware)",
            "Pass on .51 bench",
            "Pass",
            "Minicom shows readable packets at 115200; NODE=MAIN and NODE=NODE_01 lines observed",
            "minicom -D /dev/ttyUSB0 -b 115200",
            "Code deployed but live dashboard integration pending verification.",
        ],
        [
            ".53 NODE_02 / .54 NODE_03 hardware build",
            "N/A",
            "Pending hardware assembly",
            "Not Started",
            "CSI cameras installed; ESP32 + LoRa + sensors not yet assembled",
            "Physical inventory and assembly checklist",
            "Use NODE_01 wiring/firmware baseline for assembly.",
        ],
        [
            "Thermal camera (MLX90640) installation",
            "N/A",
            "Pending hardware installation",
            "Not Started",
            "Module exists in code; not physically installed on MAIN",
            "Physical installation on MAIN RPi I2C; verify /thermal_feed",
            "Deferred until thermal hardware is available.",
        ],
        [
            "Chainsaw detection / USB microphone",
            "Pass local compile/tests",
            "Pending hardware installation",
            "Not Started",
            "detector.py baseline and test audio exist; no live microphone connected",
            "python3 -m py_compile; synthetic test audio validation",
            "Deferred until USB microphone is installed on a node.",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_config_tracker(wb):
    ws = wb["Config Tracker"]
    max_row = ws.max_row
    new_rows = [
        [
            "dashboard_mode", "live", ".51 MAIN", "Field deployment 2026-06-08",
            "Approved", "MAIN .51 runs in LIVE mode; simulation still available for local dev.",
        ],
        [
            "csi_camera_status_.51", "Pass", ".51 MAIN", "Hardware validation 2026-06-08",
            "Confirmed", "CSI camera feed stable in LIVE mode.",
        ],
        [
            "csi_camera_status_.52", "Pass", ".52 NODE_01", "Hardware validation 2026-06-08",
            "Confirmed", "CSI camera feed visible on MAIN dashboard.",
        ],
        [
            "remote_aggregation_.52", "Pass", ".51 MAIN", "Integration validation 2026-06-08",
            "Confirmed", "MAIN discovers/pulls NODE_01 data and camera.",
        ],
        [
            "esp32_serial_status", "Implemented / Pending Verification", ".51 MAIN", "Serial integration 2026-06-08",
            "In Progress", "Code complete; minicom confirmed hardware; dashboard overlay pending live validation.",
        ],
        [
            "node_02_03_build_status", "Pending", ".53/.54", "Hardware build 2026-06-08",
            "Not Started", "CSI cameras installed; ESP32 + LoRa + sensors not assembled.",
        ],
        [
            "thermal_camera_status", "Pending Installation", ".51 MAIN", "Design retention 2026-06-08",
            "Approved", "Retained as MAIN-only design component; not physically installed yet.",
        ],
        [
            "chainsaw_detection_status", "Pending USB Microphone", "All nodes", "Audio pipeline 2026-06-08",
            "Not Started", "detector.py ready; USB microphone installation and live testing pending.",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_test_campaign(wb):
    ws = wb["Test Campaign"]
    max_row = ws.max_row
    new_rows = [
        [
            "T022", "CSI camera validation .51", "Open MAIN dashboard in LIVE mode and verify local camera feed",
            "Clear MJPEG stream from .51 CSI camera at configured resolution/FPS", "Stream stability", "Done",
            "Visual inspection; rpicam-hello confirmed ov5647 on .51",
        ],
        [
            "T023", "CSI camera validation .52", "Open MAIN dashboard remote camera grid and verify NODE_01 feed",
            "Clear MJPEG stream from .52 CSI camera visible on MAIN dashboard", "Stream stability", "Done",
            "Visual inspection; rpicam-hello confirmed ov5647 on .52",
        ],
        [
            "T024", "Remote node aggregation .51 to .52", "Observe MAIN dashboard sensor cards and node inventory",
            "Remote slot 1 shows NODE_01 sensor data and camera; node marked online", "Data latency / accuracy", "Done",
            "Dashboard JSON shows remote slot 1 populated; network reachability confirmed",
        ],
        [
            "T025", "MAIN ESP32 USB serial reader implementation", "Review code, run py_compile, and inspect config",
            "modules/esp32_serial_reader.py compiles; config keys present; thread-safe cache logic correct", "Code quality", "Done",
            "python3 -m py_compile passed; unit parse test passed",
        ],
        [
            "T026", "MAIN ESP32 serial hardware confirmation", "Run minicom on /dev/ttyUSB0 at 115200 and observe packets",
            "NODE=MAIN and NODE=NODE_01 packets readable; no garbled output", "Serial integrity", "Done",
            "Minicom session recorded packet examples at 115200",
        ],
        [
            "T027", "MAIN ESP32 dashboard live sensor integration", "Deploy code to .51 MAIN and observe sensor cards",
            "Local node card shows TEMP/HUM/PIR/MQ/BAT from serial cache; serial_connected=true", "Integration accuracy", "In Progress",
            "Code implemented; pending deployment and live validation. DO NOT MARK PASS YET.",
        ],
        [
            "T028", ".53/.54 hardware build readiness", "Physical inspection of NODE_02/NODE_03 assemblies",
            "ESP32 + LoRa + sensors + CSI camera wired and powered", "Hardware completeness", "Not Started",
            "CSI cameras installed; remaining components pending assembly.",
        ],
        [
            "T029", "Thermal camera installation readiness", "Inspect MAIN RPi for MLX90640 I2C connection",
            "Thermal camera mounted and /thermal_feed returns frames", "Hardware completeness", "Not Started",
            "Module exists in code; hardware not installed.",
        ],
        [
            "T030", "Chainsaw detection readiness", "Install USB microphone and run detector.py with test audio",
            "detector.py detects chainsaw-like audio and triggers alert + recording", "Detection latency / accuracy", "Not Started",
            "Synthetic test audio exists; live microphone pending.",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_known_issues(wb):
    ws = wb["Known Issues"]
    max_row = ws.max_row
    # Preserve historical USB webcam note; update CSI pipeline status
    for row in range(2, max_row + 1):
        issue = ws.cell(row=row, column=1).value
        if issue and "USB webcam compatibility blocker" in str(issue):
            ws.cell(row=row, column=3, value="Resolved")
            ws.cell(row=row, column=5, value="Replaced with Raspberry Pi Camera Rev 1.3 CSI. Historical USB findings remain documented for reference.")
        if issue and "CSI camera pipeline not yet implemented" in str(issue):
            ws.cell(row=row, column=3, value="Resolved")
            ws.cell(row=row, column=5, value="Picamera2 CSI pipeline implemented and validated on .51/.52. USB fallback preserved.")
    new_rows = [
        [
            "MAIN ESP32 dashboard live sensor integration not yet verified",
            "Medium",
            "Open",
            "Sensor cards on MAIN dashboard may still show HTTP fallback data instead of serial cache until deployment validation is complete",
            "Deploy to .51 and verify /api/status serial_connected=true and sensor card values match minicom packets.",
        ],
        [
            ".53/.54 ESP32 + LoRa + sensor hardware build pending",
            "High",
            "Open",
            "Cannot validate full 4-node mesh or complete camera grid until NODE_02/NODE_03 are assembled",
            "Assemble using NODE_01 baseline; run LoRa bench test and rpicam-hello confirmation.",
        ],
        [
            "Thermal camera (MLX90640) not installed on MAIN",
            "Medium",
            "Open",
            "Night thermal detection feature unavailable for field demo until hardware is mounted",
            "Install MLX90640 on MAIN RPi I2C and validate /thermal_feed endpoint.",
        ],
        [
            "USB microphone not installed; chainsaw detection untested",
            "Medium",
            "Open",
            "Audio alert and event recording features cannot be validated in live mode without microphone hardware",
            "Install USB microphone on a node and run detector.py with synthetic then field audio.",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_change_log(wb):
    ws = wb["Change Log"]
    max_row = ws.max_row
    new_rows = [
        [
            "C039", DATE_STR, "Dashboard",
            "MAIN .51 dashboard confirmed in LIVE mode with CSI camera and ESP32 serial integration",
            "app.py; modules/csi_camera_stream.py; modules/esp32_serial_reader.py; config.json; templates/dashboard.html; static/app.js",
            "Visual inspection on .51; rpicam-hello confirmed; minicom confirmed serial packets",
            "Pending commit",
            "Deploy to .51 and validate sensor cards populate from serial cache",
        ],
        [
            "C040", DATE_STR, "Hardware",
            "CSI camera validation .51 PASS — MAIN .51 CSI camera works in LIVE mode",
            "modules/csi_camera_stream.py; hardware/wiring_reference.md; docs/PROJECT_STATUS.md; docs/ACTIVE_CONTEXT.md",
            "rpicam-hello --list-cameras; dashboard visual inspection; curl /video_feed",
            "Pending commit",
            "Validate .52 NODE_01 camera feed on MAIN dashboard",
        ],
        [
            "C041", DATE_STR, "Hardware",
            "CSI camera validation .52 PASS — NODE_01 .52 CSI camera works and appears on MAIN dashboard",
            "modules/csi_camera_stream.py; multi_camera_stream.py; app.py; docs/PROJECT_STATUS.md; docs/ACTIVE_CONTEXT.md",
            "rpicam-hello on .52; dashboard remote camera grid inspection; /api/server-dashboard JSON",
            "Pending commit",
            "Validate remote node aggregation and sensor data sync",
        ],
        [
            "C042", DATE_STR, "Integration",
            "Remote node aggregation .51 to .52 PASS — MAIN discovers and pulls NODE_01 data and camera feed",
            "app.py; modules/node_registry.py; modules/network_utils.py; docs/PROJECT_STATUS.md; docs/ACTIVE_CONTEXT.md",
            "Dashboard inspection; network reachability; /api/server-dashboard remote slot 1 populated",
            "Pending commit",
            "Validate ESP32 serial reader live integration on .51",
        ],
        [
            "C043", DATE_STR, "Integration",
            "MAIN ESP32 USB serial reader IMPLEMENTED / PENDING VERIFICATION — modules/esp32_serial_reader.py created and integrated",
            "modules/esp32_serial_reader.py; app.py; config.json; docs/PROJECT_STATUS.md; docs/AI_SESSION_HANDOFF.md; docs/hardware/wiring_reference.md; docs/deployment/field_deployment_checklist.md",
            "python3 -m py_compile passed; parsing unit test passed; manual parse_line verification",
            "Pending commit",
            "Deploy to .51 MAIN and verify sensor cards populate from serial cache",
        ],
        [
            "C044", DATE_STR, "Hardware",
            "MAIN ESP32 serial hardware manually confirmed using Minicom on /dev/ttyUSB0 at 115200",
            "docs/PROJECT_STATUS.md; docs/ACTIVE_CONTEXT.md; docs/hardware/wiring_reference.md",
            "Minicom session captured NODE=MAIN and NODE=NODE_01 packets",
            "Pending commit",
            "Deploy serial reader code and confirm dashboard overlay in LIVE mode",
        ],
        [
            "C045", DATE_STR, "Hardware",
            ".53 NODE_02 and .54 NODE_03 marked pending hardware build — CSI cameras installed, ESP32 + sensors not assembled",
            "docs/PROJECT_STATUS.md; docs/ACTIVE_CONTEXT.md; docs/AI_SESSION_HANDOFF.md; docs/hardware/wiring_reference.md",
            "Physical inventory status",
            "Pending commit",
            "Assemble NODE_02/NODE_03 using NODE_01 baseline and validate",
        ],
        [
            "C046", DATE_STR, "Hardware",
            "Thermal camera retained as MAIN-only design component but marked pending physical installation",
            "docs/PROJECT_STATUS.md; docs/ACTIVE_CONTEXT.md; modules/thermal_camera.py",
            "Design review; module exists in code; hardware not installed",
            "Pending commit",
            "Install MLX90640 on MAIN and validate /thermal_feed",
        ],
        [
            "C047", DATE_STR, "Audio",
            "Chainsaw detection marked pending USB microphone installation and testing",
            "detector.py; test_audio/; docs/PROJECT_STATUS.md; docs/ACTIVE_CONTEXT.md",
            "Synthetic test audio exists; no live microphone hardware connected",
            "Pending commit",
            "Install USB microphone on a node and run live chainsaw detection validation",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_active_context_snapshot(wb):
    ws = wb["Active Context Snapshot"]
    for row in range(1, ws.max_row + 1):
        field = ws.cell(row=row, column=1).value
        if field == "Latest Completed Step":
            ws.cell(row=row, column=2, value="MAIN .51 dashboard LIVE mode; CSI cameras validated on .51/.52; remote node aggregation .51→.52 PASS; ESP32 serial reader implemented; minicom confirmed hardware.")
            ws.cell(row=row, column=3, value=DATE_STR)
        if field == "Current Active Milestone":
            ws.cell(row=row, column=2, value="ESP32 Serial Reader Deployment Verification Phase")
            ws.cell(row=row, column=3, value="Next: deploy to .51 and validate live sensor cards from serial.")
        if field == "Current Active Feature":
            ws.cell(row=row, column=2, value="CSI camera pipeline LIVE on .51/.52; ESP32 serial integration implemented pending verification")
            ws.cell(row=row, column=3, value="No new features until serial and remaining hardware are validated.")
        if field == "Latest Unresolved Issue":
            ws.cell(row=row, column=2, value="MAIN ESP32 dashboard live sensor integration pending verification; .53/.54 hardware build pending; thermal and audio pending hardware.")
            ws.cell(row=row, column=3, value="Serial code is complete; deploy and confirm.")
        if field == "Testing State":
            ws.cell(row=row, column=2, value="CSI camera .51/.52 PASS; remote aggregation PASS; serial hardware PASS; serial dashboard integration IN PROGRESS.")
            ws.cell(row=row, column=3, value="Pending: deploy serial reader to .51 and confirm sensor card population.")
        if field == "Current Milestone":
            ws.cell(row=row, column=2, value="Hardware bench validation extended: MAIN + NODE_01 camera and network validated; serial code ready")
            ws.cell(row=row, column=3, value="Focus on .51 deployment and sensor verification.")
        if field == "Next Recommended Action":
            ws.cell(row=row, column=2, value="Deploy updated raspi/firenode-system to .51 MAIN and validate live mode sensor cards from serial cache")
            ws.cell(row=row, column=3, value="Use SSH key ~/admfire and user betech against 192.168.9.51.")
        if field == "Next Incomplete Task":
            ws.cell(row=row, column=2, value="Deploy and verify ESP32 serial reader on .51 MAIN")
            ws.cell(row=row, column=3, value="Confirm /api/status serial_connected=true and sensor values match minicom packets.")
        if field == "Paused Work":
            ws.cell(row=row, column=2, value="None (ESP32/LoRa hardware validation resumed via serial path)")
            ws.cell(row=row, column=3, value="Previous pause lifted; serial integration now active.")
        if field == "Current Issue":
            ws.cell(row=row, column=2, value="MAIN ESP32 serial integration implemented but not yet verified in live mode")
            ws.cell(row=row, column=3, value="Code complete; minicom confirmed hardware output; deployment pending.")
        if field == "Next Recommended Action" and row != 17:
            # Avoid double-update if there are multiple rows; but we update the first match above.
            pass
        if field == "Camera Stability Default":
            ws.cell(row=row, column=2, value="CSI: 640x480, 15 FPS, JPEG quality 85. USB fallback preserved: 320x240, 10 FPS, JPEG quality 55, MJPG, 10 warmup frames.")
            ws.cell(row=row, column=3, value="CSI validated on .51/.52 in LIVE mode.")


def main():
    if not WORKBOOK.exists():
        print(f"ERROR: Workbook not found at {WORKBOOK}", file=sys.stderr)
        raise SystemExit(1)

    wb = openpyxl.load_workbook(WORKBOOK)

    update_dashboard(wb)
    update_progress_tracker(wb)
    update_issue_log(wb)
    update_decision_log(wb)
    update_build_validation_matrix(wb)
    update_config_tracker(wb)
    update_test_campaign(wb)
    update_known_issues(wb)
    update_change_log(wb)
    update_active_context_snapshot(wb)

    wb.save(WORKBOOK)
    print(f"Workbook updated: {WORKBOOK}")


if __name__ == "__main__":
    main()
