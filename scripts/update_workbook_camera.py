#!/usr/bin/env python3
"""Update the ADM FireNode workbook to reflect the final CSI camera hardware decision."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment
except Exception as exc:
    print(f"ERROR: openpyxl is required: {exc}", file=sys.stderr)
    raise SystemExit(1)

WORKBOOK = Path(__file__).resolve().parents[1] / "docs" / "workbook" / "ADM_FireNode_Implementation_Workbook.xlsx"
DATE_STR = datetime.now().strftime("%Y-%m-%d")


def update_dashboard(wb):
    ws = wb["Dashboard"]
    # Row 10 = Current Stage
    ws["B10"] = (
        "ESP32 MAIN + NODE_01 bench validated; "
        "USB webcam deprecated; Raspberry Pi Camera Rev 1.3 CSI selected; "
        "Picamera2 module implemented locally (csi_camera_stream.py); next: deploy and validate on .51/.52"
    )
    # Row 11 = Next Action
    ws["B11"] = (
        "Deploy and validate Raspberry Pi CSI camera pipeline (Picamera2) on .51 and .52. "
        "Keep thermal/ESP32/LoRa unchanged. USB microphone/chainsaw detection remains later work."
    )


def update_progress_tracker(wb):
    ws = wb["Progress Tracker"]
    # Find first empty row after existing entries (start scanning from row 4)
    max_row = ws.max_row
    # Append new progress entries
    new_rows = [
        [
            "P037", "Hardware", "Raspberry Pi Camera Rev 1.3 CSI selected as official camera hardware; USB webcam deprecated",
            "Done", "User/Codex", DATE_STR,
            "ov5647 detected on .51/.52; rpicam-hello --list-cameras confirmed",
            "Implement rpicam/libcamera capture pipeline in RPi app"
        ],
        [
            "P038", "Hardware", ".51 MAIN CSI camera detection confirmed (ov5647 [2592x1944 10-bit GBRG])",
            "Done", "User", DATE_STR,
            "rpicam-hello --list-cameras output recorded",
            "Validate still capture and integrate into app"
        ],
        [
            "P039", "Hardware",
            ".52 NODE_01 CSI camera detection confirmed (ov5647 [2592x1944 10-bit GBRG])",
            "Done", "User", DATE_STR,
            "rpicam-hello --list-cameras output recorded",
            "Validate still capture and integrate into app"
        ],
        [
            "P040", "Hardware",
            ".53 NODE_02 Raspberry Pi Camera Rev 1.3 CSI installed; pending physical confirmation",
            "In Progress", "User", DATE_STR,
            "Hardware installed; awaiting rpicam-hello confirmation",
            "Run rpicam-hello --list-cameras on .53"
        ],
        [
            "P041", "Hardware",
            ".54 NODE_03 Raspberry Pi Camera Rev 1.3 CSI installed; pending physical confirmation",
            "In Progress", "User", DATE_STR,
            "Hardware installed; awaiting rpicam-hello confirmation",
            "Run rpicam-hello --list-cameras on .54"
        ],
        [
            "P042", "Camera", "Implement Raspberry Pi CSI camera pipeline using Picamera2",
            "In Progress", "Codex/User", DATE_STR,
            "modules/csi_camera_stream.py created; multi_camera_stream.py updated; app.py/config updated; py_compile passed",
            "Deploy to .51/.52 and validate /video_feed endpoint"
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_issue_log(wb):
    ws = wb["Issue Log"]
    max_row = ws.max_row
    # Update existing USB webcam issue (I012) to resolved/deprecated status
    for row in range(4, max_row + 1):
        issue_id = ws.cell(row=row, column=1).value
        if issue_id == "I012":
            ws.cell(row=row, column=7, value="Resolved")
            ws.cell(row=row, column=8, value="USB webcam deprecated. Replaced with Raspberry Pi Camera Rev 1.3 CSI.")
        if issue_id == "I014":
            ws.cell(row=row, column=7, value="In Progress")
            ws.cell(row=row, column=8, value="modules/csi_camera_stream.py implemented; multi_camera_stream.py updated; app.py/config updated; pending deploy to .51/.52")
    # Add new issues/updates
    new_rows = [
        [
            "I015", "Hardware", ".53 NODE_02 and .54 NODE_03 CSI camera physical confirmation pending",
            "Cannot confirm ov5647 detection on .53/.54 until hardware is powered and cabled",
            "User", "Open",
            "Run rpicam-hello --list-cameras on .53 and .54 when ready.",
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
            "D007", DATE_STR,
            "Raspberry Pi Camera Rev 1.3 (ov5647) via CSI is the official daytime camera hardware",
            "USB webcam produced corrupted/distorted frames on RPi 3B; CSI camera is native, reliable, and already detected",
            "rpicam-hello --list-cameras shows ov5647 on .51 and .52",
            "All nodes use CSI ribbon camera; USB path deprecated but code fallback preserved temporarily.",
        ],
        [
            "D008", DATE_STR,
            "USB webcam path is deprecated from target design",
            "YUYV fails outright; MJPG works but frames are corrupted on RPi 3B due USB bandwidth/power limits",
            "Camera test history and rpicam-hello detection results",
            "Historical USB findings remain documented for reference only.",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_build_validation_matrix(wb):
    ws = wb["Build Validation Matrix"]
    max_row = ws.max_row
    # Append updated camera row
    new_rows = [
        [
            "RPi USB camera MJPG/V4L2 capture fix",
            "Pass local compile/tests",
            "Deprecated; USB path removed from target design",
            "N/A",
            "Replaced by CSI camera plan",
            "python3 -m py_compile; ./scripts/run_raspi_tests.sh",
            "Superseded by CSI camera implementation (P042).",
        ],
        [
            "RPi 3B camera stability defaults",
            "Pass local compile/tests",
            "Deprecated; USB path removed from target design",
            "N/A",
            "Replaced by CSI camera plan",
            "py_compile; unit tests; smoke test",
            "Superseded by CSI camera implementation (P042).",
        ],
        [
            "Raspberry Pi Camera Rev 1.3 CSI detection",
            "N/A (hardware)",
            "Pass on .51/.52",
            "Pass",
            "ov5647 detected; rpicam-hello confirmed",
            "rpicam-hello --list-cameras",
            "Detection confirmed. Pipeline module implemented; pending deploy validation.",
        ],
        [
            "Raspberry Pi Camera Rev 1.3 CSI pipeline (Picamera2)",
            "Pass local compile/tests",
            "Pending deploy validation on .51/.52",
            "In Progress",
            "modules/csi_camera_stream.py + multi_camera_stream.py + app.py updates; py_compile passed",
            "python3 -m py_compile; deploy to .51/.52; curl /video_feed",
            "CSI primary with USB fallback; simulation preserved.",
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
            "camera_type", "CSI (Raspberry Pi Camera Rev 1.3)", "All RPis", "Hardware decision 2026-06-02",
            "Approved", "Replaces USB webcam.",
        ],
        [
            "camera_capture_module", "Picamera2 (modules/csi_camera_stream.py)", "All RPis", "Implementation task P042",
            "Implemented", "New module to replace OpenCV V4L2 path for production.",
        ],
        [
            "camera_sensor", "ov5647", "All RPis", "rpicam-hello --list-cameras",
            "Confirmed", "2592x1944 10-bit GBRG.",
        ],
        [
            "camera_usb_fallback", "True", "All RPis", "app.py DEFAULT_CONFIG",
            "Approved", "If Picamera2 fails, fall back to OpenCV USB camera path.",
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
            "T011", "CSI camera detection", "Run rpicam-hello --list-cameras on each RPi",
            "ov5647 sensor appears with supported modes", "Sensor presence", "Done", ".51/.52 confirmed",
        ],
        [
            "T012", "CSI still capture", "Run rpicam-still -o /tmp/csi_test.jpg on each RPi",
            "JPEG saved without corruption", "Image clarity", "Done", "rpicam-still confirmed on .51/.52",
        ],
        [
            "T013", "CSI MJPEG stream", "Open /video_feed after app integration",
            "MJPEG stream returns clear frames at configured resolution/FPS", "Stream stability", "In Progress", "modules implemented; pending deploy to .51/.52",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_known_issues(wb):
    ws = wb["Known Issues"]
    max_row = ws.max_row
    # Update USB webcam row to resolved and CSI pipeline status
    for row in range(2, max_row + 1):
        issue = ws.cell(row=row, column=1).value
        if issue and "USB webcam compatibility blocker" in str(issue):
            ws.cell(row=row, column=3, value="Resolved")
            ws.cell(row=row, column=5, value="Replaced with Raspberry Pi Camera Rev 1.3 CSI.")
        if issue and "CSI camera pipeline not yet implemented" in str(issue):
            ws.cell(row=row, column=3, value="In Progress")
            ws.cell(row=row, column=5, value="modules/csi_camera_stream.py implemented; pending deploy to .51/.52")
    new_rows = [
        [
            ".53/.54 CSI camera physical confirmation pending",
            "Medium",
            "Open",
            "Cannot confirm ov5647 detection on NODE_02/NODE_03 until hardware is cabled and powered",
            "Run rpicam-hello --list-cameras on .53 and .54.",
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
            "C027", DATE_STR, "Hardware",
            "Finalized Raspberry Pi Camera Rev 1.3 CSI as official camera hardware; deprecated USB webcam",
            "docs/ACTIVE_CONTEXT.md; docs/PROJECT_STATUS.md; docs/AI_SESSION_HANDOFF.md; docs/hardware/wiring_reference.md; docs/deployment/field_deployment_checklist.md; workbook",
            "Documentation review; rpicam-hello detection confirmed on .51/.52",
            "Committed",
            "Implement rpicam/libcamera capture pipeline (P042)",
        ],
        [
            "C028", DATE_STR, "Hardware",
            ".51 MAIN and .52 NODE_01 CSI camera detection confirmed (ov5647)",
            "docs/PROJECT_STATUS.md; docs/AI_SESSION_HANDOFF.md; workbook",
            "rpicam-hello --list-cameras output recorded",
            "Committed",
            "Integrate rpicam/libcamera into camera_stream.py and validate stream endpoint",
        ],
        [
            "C029", DATE_STR, "Camera",
            "Implemented modules/csi_camera_stream.py with Picamera2; updated multi_camera_stream.py, app.py, config, dashboard UI",
            "modules/csi_camera_stream.py; modules/multi_camera_stream.py; app.py; config.json; requirements.txt; templates/dashboard.html; static/app.js",
            "py_compile validation passed; CSI primary with USB fallback; simulation preserved",
            "Pending commit",
            "Deploy to .51/.52 and validate /video_feed endpoint",
        ],
    ]
    for row in new_rows:
        max_row += 1
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=max_row, column=col_idx, value=value)


def update_active_context_snapshot(wb):
    ws = wb["Active Context Snapshot"]
    # Row 10 = Current Stage
    for row in range(1, ws.max_row + 1):
        if ws.cell(row=row, column=1).value == "Current Stage":
            ws.cell(row=row, column=2, value="USB webcam deprecated; Raspberry Pi Camera Rev 1.3 CSI selected; Picamera2 module implemented locally; next: deploy and validate on .51/.52")
        if ws.cell(row=row, column=1).value == "Next Recommended Action":
            ws.cell(row=row, column=2, value="Deploy and validate Raspberry Pi CSI camera pipeline (Picamera2) on .51 and .52")
        if ws.cell(row=row, column=1).value == "Camera Stability Default":
            ws.cell(row=row, column=2, value="CSI: 640x480, 15 FPS, JPEG quality 85. USB fallback preserved: 320x240, 10 FPS, JPEG quality 55, MJPG, 10 warmup frames.")


def main():
    if not WORKBOOK.exists():
        print(f"ERROR: workbook not found at {WORKBOOK}", file=sys.stderr)
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
