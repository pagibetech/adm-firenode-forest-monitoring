#!/usr/bin/env python3
"""
FireNode RPi Unified Main Server / Node Web Application

Target: Raspberry Pi OS Legacy Lite 32-bit on Raspberry Pi 3B.

This version is intended for the main-server RPi by default. It can still be
changed to Node mode from the web GUI when the same package is installed on the
other three RPis.

Main-server functions:
- Display local USB webcam streams from this RPi.
- Display the local MLX90640 thermal stream and human-detection status.
- Pull /api/node-data from the three other RPi nodes.
- Display remote webcam/thermal streams exposed by those RPis.
- Display ESP32 sensor data, chainsaw status, PIR/thermal human status, and alerts.

Node functions:
- Select and read one ESP32 FireNode JSON endpoint at http://<esp32-ip>/data.
- Expose local camera/thermal/chainsaw/sensor status through /api/node-data.
- Provide streams that the main server can display.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Flask, Response, jsonify, render_template, request, send_file, send_from_directory

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = ImageDraw = ImageFont = None

from detector import (
    ChainsawDetector,
    SUPPORTED_AUDIO_EXTS,
    analyze_audio_file,
    is_supported_audio,
    save_config as save_detector_config,
)
from modules.alert_logger import AlertLogger
from modules.event_recorder import EventRecorder
from modules.esp32_client import fetch_esp32_data, normalize_ip
from modules.esp32_scanner import scan_esp32_devices
from modules.esp32_serial_reader import ESP32SerialReader, serial_data_to_esp32_format, sensor_summary_from_serial
from modules.lora_packet_store import LoraPacketStore
from modules.lora_simulator import LoraPacketSimulator
from modules.multi_camera_stream import MultiCameraManager, parse_camera_indexes
from modules.network_utils import get_network_summary, get_primary_ip, node_name_from_ip, subnet_prefix_from_ip
from modules.node_registry import pull_nodes, scan_rpi_nodes
from modules.thermal_camera import ThermalCameraService

APP_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")
TEST_AUDIO_DIR = os.path.join(APP_DIR, "test_audio")
LOG_DIR = os.path.join(APP_DIR, "logs")
ALERT_DB = os.path.join(LOG_DIR, "alerts.db")
LORA_DB = os.path.join(LOG_DIR, "lora_packets.db")
REMOTE_NODE_COUNT = 3

DEFAULT_CONFIG: Dict[str, Any] = {
    # FireNode role. This package is now main-server oriented by default.
    "role": "server",  # server/main_server or node/node_01/node_02/node_03
    "app_role": "server",  # normalized internal role: node or server
    "operation_mode": "live",  # live or simulation
    "remote_node_count": REMOTE_NODE_COUNT,
    "host": "0.0.0.0",
    "port": 8090,
    "node_name_mode": "rpi_ip",

    # ESP32 /data reading
    "selected_esp32_ip": "",
    "esp32_scan_prefix": "auto",
    "esp32_fetch_timeout": 1.2,
    "esp32_scan_timeout": 0.55,
    "esp32_scan_workers": 48,

    # Main server mode
    "remote_node_ips": [],
    "node_scan_prefix": "auto",
    "node_scan_timeout": 0.75,
    "node_pull_timeout": 1.2,
    "server_refresh_sec": 3,

    # LoRa telemetry. Simulation mode uses this packet contract before real SX127x receive is wired in.
    "lora_enabled": True,
    "lora_sim_interval_sec": 5,
    "lora_frequency_mhz": 433.0,
    "lora_spreading_factor": 7,
    "lora_bandwidth_khz": 125.0,

    # ESP32 USB serial reader (MAIN RPi local serial)
    "esp32_serial_enabled": True,
    "esp32_serial_port": "/dev/ttyUSB0",
    "esp32_serial_baud": 115200,

    # Local cameras. camera_type = "csi" uses Picamera2; "usb" uses OpenCV V4L2 fallback.
    "camera_enabled": True,
    "camera_type": "csi",
    "camera_device_index": 0,
    "camera_device_indexes": [0],
    "camera_backend": "V4L2",
    "camera_fourcc": "MJPG",
    "camera_usb_fallback": True,
    "camera_open_warmup_frames": 10,
    "camera_retry_on_failed_read": True,
    "camera_width": 640,
    "camera_height": 480,
    "camera_fps": 15,
    "camera_jpeg_quality": 85,

    # Local MLX90640 thermal camera. It can fall back to simulation if the sensor/library is unavailable.
    "thermal_enabled": True,
    "thermal_simulation": False,
    "thermal_i2c_address": "0x33",
    "thermal_refresh_rate_hz": 2,
    "thermal_display_min_c": 20.0,
    "thermal_display_max_c": 45.0,
    "thermal_min_human_temp_c": 28.0,
    "thermal_max_human_temp_c": 42.0,
    "thermal_min_delta_above_ambient_c": 4.0,
    "thermal_min_blob_pixels": 5,
    "thermal_rotate_degrees": 0,
    "thermal_mirror_x": False,
    "thermal_mirror_y": False,

    # Wi-Fi settings are stored so the field technician can keep node credentials in one place.
    # Applying OS Wi-Fi is intentionally manual to avoid disconnecting a remote session unexpectedly.
    "wifi_ssid": "",
    "wifi_password": "",
    "wifi_country": "PH",
    "wifi_interface": "wlan0",

    # Chainsaw detector settings from the attached program
    "sample_rate": 16000,
    "window_sec": 1.0,
    "score_threshold": 60,
    "min_rms": 0.015,
    "require_hits": 3,
    "history_windows": 5,
    "cooldown_sec": 30,
    "auto_start": True,
    "detection_mode": "live",  # live or file
    "input_device": None,
    "audio_browse_start_dir": "test_audio",
    "log_file": "detections.csv",
    "event_recording_enabled": True,
}

app = Flask(__name__)


def get_lan_urls(port: int) -> List[str]:
    """Return useful LAN URLs for the technician to open from another device."""
    ips: List[str] = []
    try:
        out = subprocess.check_output(["hostname", "-I"], text=True, timeout=2, stderr=subprocess.DEVNULL)
        for part in out.split():
            part = part.strip()
            if part and part not in ips and not part.startswith("127.") and ":" not in part:
                ips.append(part)
    except Exception:
        pass
    try:
        primary = get_primary_ip()
        if primary and primary not in ips and not primary.startswith("127."):
            ips.insert(0, primary)
    except Exception:
        pass
    return [f"http://{ip}:{port}" for ip in ips]


def is_port_available(host: str, port: int) -> bool:
    """Check before starting cameras/audio so a stale server is reported clearly."""
    bind_host = host if host not in ("0.0.0.0", "::") else ""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((bind_host, port))
        return True
    except OSError:
        return False


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_role(value: Any) -> str:
    """Map deployment labels to the app's internal server/node roles."""
    role = str(value or "server").strip().lower().replace("-", "_")
    if role in ("main_server", "main", "server", "node_main_center", "node_main"):
        return "server"
    if role in ("node", "node_01", "node_02", "node_03", "node_1", "node_2", "node_3"):
        return "node"
    return "server"


def load_config() -> Dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except Exception:
            pass
    cfg["app_role"] = normalize_role(cfg.get("role"))
    if cfg.get("detection_mode") not in ("live", "file"):
        cfg["detection_mode"] = "live"
    if cfg.get("operation_mode") not in ("live", "simulation"):
        cfg["operation_mode"] = "live"
    cfg["remote_node_count"] = REMOTE_NODE_COUNT
    if not isinstance(cfg.get("remote_node_ips"), list):
        cfg["remote_node_ips"] = []
    cfg["remote_node_ips"] = [str(x).strip() for x in cfg.get("remote_node_ips", []) if str(x).strip()][:REMOTE_NODE_COUNT]
    cfg["camera_device_indexes"] = parse_camera_indexes(cfg.get("camera_device_indexes", [cfg.get("camera_device_index", 0)]), int(cfg.get("camera_device_index", 0)))
    cfg["camera_device_index"] = int(cfg["camera_device_indexes"][0])
    return cfg


def save_config() -> None:
    os.makedirs(APP_DIR, exist_ok=True)
    safe = dict(DEFAULT_CONFIG)
    safe.update(cfg)
    safe["camera_device_indexes"] = parse_camera_indexes(safe.get("camera_device_indexes", [safe.get("camera_device_index", 0)]), int(safe.get("camera_device_index", 0)))
    safe["camera_device_index"] = int(safe["camera_device_indexes"][0])
    safe["remote_node_count"] = REMOTE_NODE_COUNT
    safe["app_role"] = normalize_role(safe.get("role"))
    if safe.get("operation_mode") not in ("live", "simulation"):
        safe["operation_mode"] = "live"
    if isinstance(safe.get("remote_node_ips"), list):
        safe["remote_node_ips"] = [str(x).strip() for x in safe.get("remote_node_ips", []) if str(x).strip()][:REMOTE_NODE_COUNT]
    else:
        safe["remote_node_ips"] = []
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(safe, f, indent=2)


cfg: Dict[str, Any] = load_config()
# Keep detector.py defaults merged with app config.
save_detector_config(cfg, CONFIG_PATH)

alert_logger = AlertLogger(ALERT_DB)
lora_store = LoraPacketStore(LORA_DB)
event_recorder = EventRecorder(os.path.join(APP_DIR, "media"), lambda: cfg)
detector = ChainsawDetector(cfg, APP_DIR)
cameras = MultiCameraManager(lambda: cfg)
thermal = ThermalCameraService(lambda: cfg)
lora_simulator = LoraPacketSimulator(lambda: cfg)
last_alert_states: Dict[str, bool] = {}

esp32_serial_reader: Optional[ESP32SerialReader] = None


def current_role() -> str:
    return normalize_role(cfg.get("role", cfg.get("app_role", "server")))


def operation_mode() -> str:
    if current_role() == "node":
        return "live"
    return "simulation" if str(cfg.get("operation_mode", "live")).lower() == "simulation" else "live"


def get_scan_prefix(kind: str = "esp32") -> str:
    key = "esp32_scan_prefix" if kind == "esp32" else "node_scan_prefix"
    val = str(cfg.get(key) or "auto").strip().lower()
    if not val or val == "auto":
        return subnet_prefix_from_ip(get_primary_ip())
    val = val.replace("/24", "")
    parts = val.split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3])
    return subnet_prefix_from_ip(get_primary_ip())


def public_base_url(ip: Optional[str] = None) -> str:
    ip = ip or get_primary_ip()
    return f"http://{ip}:{int(cfg.get('port', 8090))}"


def local_node_name() -> str:
    return node_name_from_ip(get_primary_ip())


def resolve_path(path_text: Optional[str]) -> str:
    if not path_text:
        path_text = str(cfg.get("audio_browse_start_dir") or TEST_AUDIO_DIR)
    path_text = os.path.expanduser(str(path_text))
    if not os.path.isabs(path_text):
        path_text = os.path.join(APP_DIR, path_text)
    return os.path.abspath(path_text)


def drive_shortcuts() -> List[Dict[str, str]]:
    candidates = [
        ("Included Test Audio", TEST_AUDIO_DIR),
        ("Application Folder", APP_DIR),
        ("Home Folder", os.path.expanduser("~")),
        ("Mounted Drives - /media", "/media"),
        ("Mounted Drives - /mnt", "/mnt"),
        ("Root - /", "/"),
    ]
    data: List[Dict[str, str]] = []
    seen = set()
    for label, path in candidates:
        abspath = os.path.abspath(os.path.expanduser(path))
        if abspath in seen:
            continue
        seen.add(abspath)
        if os.path.exists(abspath):
            data.append({"label": label, "path": abspath})
    return data



def make_simulated_esp32_data(slot: int = 0) -> Dict[str, Any]:
    """Small deterministic simulation so the GUI can be demonstrated without ESP32/RPi nodes."""
    t = time.time()
    phase = t / 8.0 + (slot * 0.9)
    temp = 30.0 + (slot * 0.7) + 2.0 * math.sin(phase)
    hum = 68.0 + 8.0 * math.cos(phase / 1.4)
    smoke_raw = int(170 + slot * 35 + 80 * max(0, math.sin(phase / 2.2)))
    smoke_detected = bool(slot == 3 and int(t / 30) % 2 == 1)
    pir_human = bool(slot == 2 and int(t / 18) % 2 == 0)
    return {
        "node_id": f"SIM-ESP32-{slot}",
        "simulation": True,
        "temperature": round(temp, 1),
        "humidity": round(hum, 1),
        "smoke": smoke_raw,
        "smoke_ppm": smoke_raw,
        "smoke_detected": smoke_detected,
        "pir": 1 if pir_human else 0,
        "human_detected": pir_human,
        "dht_valid": True,
        "lora_ready": True,
        "last_lora_send_ok": True,
    }


def make_simulated_thermal_status(slot: int = 0) -> Dict[str, Any]:
    t = time.time()
    active = bool(slot == 2 and int(t / 18) % 2 == 0)
    ambient = 27.5 + slot * 0.3
    max_temp = (35.0 + 1.5 * math.sin(t / 5.0)) if active else (29.0 + 0.8 * math.sin(t / 6.0 + slot))
    return {
        "enabled": True,
        "running": True,
        "simulation": True,
        "error": None,
        "detection": {
            "human_detected": active,
            "reason": "simulation demo human" if active else "simulation clear",
            "ambient_c": round(ambient, 2),
            "max_temp_c": round(max_temp, 2),
            "min_temp_c": round(ambient - 1.5, 2),
            "avg_temp_c": round(ambient + 0.5, 2),
            "largest_blob_pixels": 12 if active else 0,
            "bbox": [9, 6, 18, 17] if active else None,
            "score": 82 if active else 12,
        },
    }


def make_simulated_chainsaw_status(slot: int = 0) -> Dict[str, Any]:
    t = time.time()
    active = bool(slot == 3 and int(t / 24) % 2 == 0)
    return {
        "running": True,
        "confirmed_detection": active,
        "instant_detection": active,
        "score": 88 if active else 18,
        "rms": 0.12 if active else 0.018,
        "last_update": now_text(),
        "alerts_total": 0,
        "error": None,
        "simulation": True,
    }


def make_placeholder_remote_node(slot: int, ip: str = "", error: str = "") -> Dict[str, Any]:
    label = f"Remote Node {slot} Video Placeholder"
    message = f"Waiting for Remote Node {slot} IP in Settings." if not ip else f"Configured IP {ip} is offline or not responding."
    if error:
        message = error
    return {
        "firenode_api": True,
        "timestamp": now_text(),
        "role": "node",
        "remote_slot": slot,
        "expected_remote_slot": True,
        "placeholder": True,
        "online": False,
        "node_name": f"Remote-Node-{slot}",
        "rpi_ip": ip,
        "ip": ip,
        "base_url": f"http://{ip}:{int(cfg.get('port', 8090))}" if ip else "",
        "url": f"http://{ip}:{int(cfg.get('port', 8090))}/api/node-data" if ip else "",
        "error": message,
        "esp32_ok": False,
        "esp32_ip": "",
        "sensor_summary": {
            "temperature": None,
            "humidity": None,
            "smoke_raw": None,
            "smoke_detected": False,
            "pir_raw": None,
            "human_detected": False,
            "thermal_human_detected": False,
            "thermal_max_temp_c": None,
            "simulation": False,
        },
        "chainsaw": {"running": False, "confirmed_detection": False, "instant_detection": False, "score": None, "error": "offline"},
        "thermal": {"enabled": False, "running": False, "simulation": False, "detection": {"human_detected": False}},
        "camera": {"enabled": False, "camera_count": 0},
        "video_urls": [{
            "type": "remote_camera_placeholder",
            "label": label,
            "placeholder": True,
            "message": message,
            "slot": slot,
        }],
    }


def make_simulated_remote_node(slot: int) -> Dict[str, Any]:
    base_url = public_base_url(get_primary_ip())
    esp32_data = make_simulated_esp32_data(slot)
    thermal_status = make_simulated_thermal_status(slot)
    chainsaw_status = make_simulated_chainsaw_status(slot)
    lora_packet = lora_simulator.packet_for_node(slot, f"Remote-Node-{slot}-SIM", esp32_data, chainsaw_status, thermal_status)
    lora_store.record(lora_packet)
    return {
        "firenode_api": True,
        "timestamp": now_text(),
        "role": "node",
        "remote_slot": slot,
        "expected_remote_slot": True,
        "simulation": True,
        "online": True,
        "node_name": f"Remote-Node-{slot}-SIM",
        "rpi_ip": f"192.168.0.10{slot}",
        "base_url": f"simulation://remote-node-{slot}",
        "url": f"simulation://remote-node-{slot}/api/node-data",
        "esp32_ok": True,
        "esp32_ip": f"SIM-ESP32-{slot}",
        "esp32": esp32_data,
        "lora": lora_packet,
        "sensor_summary": {
            "temperature": esp32_data.get("temperature"),
            "humidity": esp32_data.get("humidity"),
            "smoke_raw": esp32_data.get("smoke"),
            "smoke_detected": bool(esp32_data.get("smoke_detected", False)),
            "pir_raw": esp32_data.get("pir"),
            "human_detected": bool(esp32_data.get("human_detected", False)),
            "thermal_human_detected": bool((thermal_status.get("detection") or {}).get("human_detected", False)),
            "thermal_max_temp_c": (thermal_status.get("detection") or {}).get("max_temp_c"),
            "thermal_ambient_c": (thermal_status.get("detection") or {}).get("ambient_c"),
            "dht_valid": True,
            "simulation": True,
            "lora_ready": True,
            "last_lora_send_ok": True,
            "last_lora_seq": lora_packet.get("seq"),
            "lora_rssi_dbm": lora_packet.get("rssi_dbm"),
            "lora_snr_db": lora_packet.get("snr_db"),
            "lora_pdr_estimate_pct": lora_packet.get("pdr_estimate_pct"),
            "battery_v": (lora_packet.get("payload") or {}).get("battery_v"),
        },
        "chainsaw": chainsaw_status,
        "thermal": thermal_status,
        "camera": {"enabled": True, "camera_count": 1, "simulation": True},
        "video_url": f"{base_url}/sim_node_feed/{slot}",
        "video_urls": [{
            "type": "simulation_camera",
            "label": f"Remote Node {slot} Simulated Camera",
            "url": f"{base_url}/sim_node_feed/{slot}",
            "running": True,
            "simulation": True,
            "slot": slot,
        }],
    }


def _overlay_serial_remote_node(node: Dict[str, Any], slot: int) -> Dict[str, Any]:
    if not cfg.get("esp32_serial_enabled") or esp32_serial_reader is None:
        return node
    node_id = {1: "NODE_01", 2: "NODE_02", 3: "NODE_03"}.get(slot)
    if not node_id:
        return node
    serial_data = esp32_serial_reader.get_cache().get(node_id)
    if not serial_data:
        return node
    esp32_data = serial_data_to_esp32_format(serial_data)
    sensor_summary = sensor_summary_from_serial(serial_data)
    if node.get("placeholder"):
        ip = str(node.get("rpi_ip") or node.get("ip") or "")
        base_url = f"http://{ip}:{int(cfg.get('port', 8090))}" if ip else ""
        return {
            "firenode_api": True,
            "timestamp": now_text(),
            "role": "node",
            "remote_slot": slot,
            "expected_remote_slot": True,
            "online": True,
            "node_name": node.get("node_name") or node_name_from_ip(ip) or f"Remote-Node-{slot}",
            "rpi_ip": ip,
            "ip": ip,
            "base_url": base_url,
            "url": f"{base_url}/api/node-data" if base_url else "",
            "esp32_ok": True,
            "esp32_ip": node_id,
            "esp32": esp32_data,
            "sensor_summary": sensor_summary,
            "chainsaw": {"running": False, "confirmed_detection": False, "instant_detection": False, "score": None, "error": "offline"},
            "thermal": {"enabled": False, "running": False, "simulation": False, "detection": {"human_detected": False}},
            "camera": {"enabled": False, "camera_count": 0},
            "video_urls": [{
                "type": "remote_camera_placeholder",
                "label": f"Remote Node {slot} Video Placeholder",
                "placeholder": True,
                "message": "Node sensor data available via LoRa serial; remote RPi camera offline.",
                "slot": slot,
            }],
        }
    node["esp32_ok"] = True
    node["esp32_ip"] = node_id
    node["esp32"] = esp32_data
    existing_summary = node.get("sensor_summary") or {}
    for key in list(sensor_summary.keys()):
        existing_summary[key] = sensor_summary[key]
    node["sensor_summary"] = existing_summary
    return node


def build_remote_slots(remote_ips: List[str]) -> List[Dict[str, Any]]:
    """Always return exactly three remote node slots for the main-server dashboard."""
    clean_ips = []
    local_ip = get_primary_ip()
    for ip in remote_ips or []:
        ip = normalize_ip(str(ip or ""))
        if ip and ip != local_ip and ip not in clean_ips:
            clean_ips.append(ip)
        if len(clean_ips) >= REMOTE_NODE_COUNT:
            break
    clean_ips += [""] * (REMOTE_NODE_COUNT - len(clean_ips))

    if operation_mode() == "simulation":
        return [make_simulated_remote_node(slot) for slot in range(1, REMOTE_NODE_COUNT + 1)]

    requested_ips = [ip for ip in clean_ips if ip]
    pulled = pull_nodes(
        requested_ips,
        port=int(cfg.get("port", 8090)),
        timeout=float(cfg.get("node_pull_timeout", 1.2)),
    ) if requested_ips else []
    by_ip: Dict[str, Dict[str, Any]] = {}
    for node in pulled:
        key = normalize_ip(str(node.get("rpi_ip") or node.get("ip") or ""))
        if key:
            by_ip[key] = node

    slots: List[Dict[str, Any]] = []
    for idx, ip in enumerate(clean_ips, start=1):
        if ip and ip in by_ip:
            node = by_ip[ip]
            node["remote_slot"] = idx
            node["expected_remote_slot"] = True
            if not node.get("node_name"):
                node["node_name"] = f"Remote-Node-{idx}"
            if not node.get("video_urls") and not node.get("video_url"):
                node["video_urls"] = [{
                    "type": "remote_camera_placeholder",
                    "label": f"Remote Node {idx} Video Placeholder",
                    "placeholder": True,
                    "message": "Node is online but did not expose a video stream URL.",
                    "slot": idx,
                }]
            slots.append(node)
        else:
            slots.append(make_placeholder_remote_node(idx, ip))
    for i, node in enumerate(slots):
        slots[i] = _overlay_serial_remote_node(node, i + 1)
    return slots


def simulated_alert_rows(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for n in nodes:
        if not n.get("simulation"):
            continue
        name = str(n.get("node_name") or "Simulated Node")
        s = n.get("sensor_summary") or {}
        c = n.get("chainsaw") or {}
        t = n.get("thermal") or {}
        td = t.get("detection") or {}
        if s.get("smoke_detected"):
            rows.append({"timestamp": now_text(), "node_name": name, "source": "SIM Smoke", "event_type": "SMOKE", "severity": "SIM", "message": "Simulation: smoke alert active"})
        if s.get("human_detected"):
            rows.append({"timestamp": now_text(), "node_name": name, "source": "SIM PIR", "event_type": "HUMAN", "severity": "SIM", "message": "Simulation: PIR human motion active"})
        if td.get("human_detected"):
            rows.append({"timestamp": now_text(), "node_name": name, "source": "SIM MLX90640", "event_type": "HUMAN", "severity": "SIM", "message": "Simulation: thermal human alert active"})
        if c.get("confirmed_detection"):
            rows.append({"timestamp": now_text(), "node_name": name, "source": "SIM Audio", "event_type": "CHAINSAW", "severity": "SIM", "message": "Simulation: chainsaw alert active"})
    return rows

def build_video_streams(base_url: str, cam_status: Dict[str, Any], thermal_status: Dict[str, Any]) -> List[Dict[str, Any]]:
    streams: List[Dict[str, Any]] = []
    for cam in cam_status.get("cameras", []) or []:
        idx = int(cam.get("device_index", 0))
        cam_type = cam.get("camera_type", "usb")
        if cam_type == "csi":
            label = "Raspberry Pi CSI Camera"
            stream_type = "csi_camera"
        else:
            label = f"USB Camera /dev/video{idx}"
            stream_type = "usb_camera"
        streams.append({
            "type": stream_type,
            "label": label,
            "url": f"{base_url}/video_feed/{idx}",
            "device_index": idx,
            "running": bool(cam.get("running")),
            "error": cam.get("error"),
        })
    if bool(thermal_status.get("enabled", False)):
        streams.append({
            "type": "thermal",
            "label": "MLX90640 Thermal Camera",
            "url": f"{base_url}/thermal_feed",
            "running": bool(thermal_status.get("running")),
            "human_detected": bool((thermal_status.get("detection") or {}).get("human_detected", False)),
            "error": thermal_status.get("error"),
        })
    return streams


def detect_alert_transitions(node_name: str, esp32_data: Dict[str, Any], chainsaw_status: Dict[str, Any], thermal_status: Dict[str, Any]) -> None:
    thermal_detection = thermal_status.get("detection") or {}
    events = {
        "smoke": bool(esp32_data.get("smoke_detected", False)),
        "pir_human": bool(esp32_data.get("human_detected", False)),
        "thermal_human": bool(thermal_detection.get("human_detected", False)),
        "chainsaw": bool(chainsaw_status.get("confirmed_detection", False)),
    }
    messages = {
        "smoke": "MQ2 smoke sensor detected smoke",
        "pir_human": "PIR detected human motion",
        "thermal_human": "MLX90640 detected a human-like thermal blob",
        "chainsaw": "USB microphone detected chainsaw-like sound",
    }
    sources = {
        "smoke": "ESP32 MQ2",
        "pir_human": "ESP32 PIR",
        "thermal_human": "RPi MLX90640",
        "chainsaw": "RPi USB Mic",
    }
    event_type_map = {
        "smoke": "SMOKE",
        "pir_human": "HUMAN",
        "thermal_human": "HUMAN",
        "chainsaw": "CHAINSAW",
    }
    for event_key, active in events.items():
        key = f"{node_name}:{event_key}"
        previous = bool(last_alert_states.get(key, False))
        if active and not previous:
            details = json.dumps({"esp32": esp32_data, "chainsaw": chainsaw_status, "thermal": thermal_status})[:2000]
            alert_logger.log(node_name, sources[event_key], event_type_map[event_key], "ALERT", messages[event_key], details)
            if event_key == "chainsaw":
                try:
                    primary_idx = int(cfg.get("camera_device_index", 0))
                    frame = cameras.get_stream(primary_idx).get_frame()
                    record = event_recorder.record_snapshot_event(
                        node_name,
                        "CHAINSAW",
                        {"source": sources[event_key], "message": messages[event_key], "chainsaw": chainsaw_status},
                        frame_jpeg=frame,
                    )
                    if record.get("ok"):
                        alert_logger.log(node_name, "Camera Recorder", "RECORDING", "INFO", "Chainsaw camera snapshot recorded", json.dumps(record)[:2000])
                except Exception as exc:
                    alert_logger.log(node_name, "Camera Recorder", "RECORDING", "WARN", f"Chainsaw recording failed: {exc}")
        last_alert_states[key] = active


def detect_remote_alerts(remote_nodes: List[Dict[str, Any]]) -> None:
    for node in remote_nodes:
        if node.get("online") is False:
            continue
        node_name = str(node.get("node_name") or node.get("rpi_ip") or node.get("ip") or "RemoteNode")
        esp32_data = node.get("esp32") if isinstance(node.get("esp32"), dict) else {}
        chainsaw_status = node.get("chainsaw") if isinstance(node.get("chainsaw"), dict) else {}
        thermal_status = node.get("thermal") if isinstance(node.get("thermal"), dict) else {}
        detect_alert_transitions(node_name, esp32_data, chainsaw_status, thermal_status)


def get_local_node_data(include_alert_update: bool = True) -> Dict[str, Any]:
    net = get_network_summary()
    rpi_ip = net["rpi_ip"]
    node_name = net["node_name"]
    base_url = public_base_url(rpi_ip)

    selected_esp32_ip = normalize_ip(str(cfg.get("selected_esp32_ip") or ""))
    if operation_mode() == "simulation":
        esp32_data = make_simulated_esp32_data(0)
        esp32_result = {
            "ok": True,
            "ip": "SIMULATED",
            "url": "simulation://local-esp32/data",
            "elapsed_ms": 0,
            "data": esp32_data,
        }
    else:
        serial_data = None
        if cfg.get("esp32_serial_enabled") and esp32_serial_reader is not None:
            cache = esp32_serial_reader.get_cache()
            if current_role() == "node":
                # Try to find the cache entry matching this node's own ID
                # Use hostname suffix (e.g., firenode-node01 -> NODE_01)
                import socket
                host = socket.gethostname()
                own_id = None
                for part in host.split("-"):
                    if part.startswith("node"):
                        own_id = part.upper().replace("NODE", "NODE_")
                # Also try cache keys that contain the node numeric suffix
                best = None
                for node_id, data in cache.items():
                    if node_id == "MAIN":
                        continue
                    # Priority 1: own_id match with temp
                    if own_id and node_id == own_id and data.get("temperature") is not None:
                        serial_data = data
                        break
                if not serial_data:
                    for node_id, data in cache.items():
                        if node_id == "MAIN":
                            continue
                        has_bat = data.get("bat") is not None
                        has_temp = data.get("temperature") is not None
                        if has_temp and has_bat:
                            serial_data = data
                            break
                if not serial_data:
                    for node_id, data in cache.items():
                        if node_id == "MAIN":
                            continue
                        if data.get("temperature") is not None:
                            if best is None or (data.get("bat") is not None and best.get("bat") is None):
                                best = data
                if best is not None:
                    serial_data = best
                if not serial_data:
                    for node_id, data in cache.items():
                        if node_id != "MAIN":
                            serial_data = data
                            break
                if not serial_data and cache:
                    serial_data = next(iter(cache.values()))
            else:
                serial_data = cache.get("MAIN")
        if serial_data:
            esp32_data = serial_data_to_esp32_format(serial_data)
            esp32_result = {
                "ok": True,
                "ip": "SERIAL",
                "url": f"serial://{serial_data.get('node_id', 'UNKNOWN')}",
                "elapsed_ms": 0,
                "data": esp32_data,
            }
        elif current_role() == "node" and cfg.get("esp32_serial_enabled") and esp32_serial_reader is not None:
            serial_status = esp32_serial_reader.get_status()
            err_msg = str(serial_status.get("serial_error") or "")
            is_port_missing = bool(err_msg and ("could not open" in err_msg.lower() or "no such file" in err_msg.lower()))
            if serial_status.get("serial_connected"):
                esp32_result = {
                    "ok": False,
                    "ip": "",
                    "error": "ESP32 Local Serial: Waiting for UART data",
                }
            elif err_msg and not is_port_missing:
                esp32_result = {
                    "ok": False,
                    "ip": "",
                    "error": f"ESP32 Local Serial: {err_msg}",
                }
            else:
                esp32_result = {
                    "ok": False,
                    "ip": "",
                    "error": "ESP32 Local Serial: Waiting for UART data",
                }
            esp32_data = {}
        elif selected_esp32_ip:
            esp32_result = fetch_esp32_data(selected_esp32_ip, timeout=float(cfg.get("esp32_fetch_timeout", 1.2)))
            esp32_data = esp32_result.get("data") if esp32_result.get("ok") else {}
        else:
            if current_role() == "node":
                esp32_result = {
                    "ok": False,
                    "ip": "",
                    "error": "ESP32 Local Serial: Waiting for UART data",
                }
            else:
                esp32_result = {
                    "ok": False,
                    "ip": "",
                    "error": "No ESP32 selected. Use Scan ESP32 and Select.",
                }
            esp32_data = {}
    if not isinstance(esp32_data, dict):
        esp32_data = {}

    chainsaw_status = detector.get_status()
    cam_status = cameras.get_status()
    thermal_status = thermal.get_status()
    lora_packet = {}
    if operation_mode() == "simulation":
        lora_packet = lora_simulator.packet_for_node(0, node_name, esp32_data, chainsaw_status, thermal_status)
        lora_store.record(lora_packet)

    if include_alert_update and operation_mode() != "simulation":
        detect_alert_transitions(node_name, esp32_data, chainsaw_status, thermal_status)

    video_streams = build_video_streams(base_url, cam_status, thermal_status)
    primary_camera_url = f"{base_url}/video_feed/{int(cam_status.get('device_index', cfg.get('camera_device_index', 0)))}"

    data = {
        "firenode_api": True,
        "timestamp": now_text(),
        "role": current_role(),
        "operation_mode": operation_mode(),
        "remote_node_count": REMOTE_NODE_COUNT,
        "node_name": node_name,
        "rpi_ip": rpi_ip,
        "base_url": base_url,
        # Backward-compatible primary video field.
        "video_url": primary_camera_url,
        "video_urls": video_streams,
        "thermal_url": f"{base_url}/thermal_feed" if bool(thermal_status.get("enabled", False)) else "",
        "config_port": int(cfg.get("port", 8090)),
        "esp32_ip": selected_esp32_ip,
        "esp32_ok": bool(esp32_result.get("ok")),
        "esp32_error": esp32_result.get("error"),
        "esp32_url": esp32_result.get("url"),
        "esp32_elapsed_ms": esp32_result.get("elapsed_ms"),
        "esp32": esp32_data,
        "sensor_summary": {
            "temperature": esp32_data.get("temperature"),
            "humidity": esp32_data.get("humidity"),
            "smoke_raw": esp32_data.get("smoke"),
            "smoke_detected": bool(esp32_data.get("smoke_detected", False)),
            "pir_raw": esp32_data.get("pir"),
            "human_detected": bool(esp32_data.get("human_detected", False)),
            "thermal_human_detected": bool((thermal_status.get("detection") or {}).get("human_detected", False)),
            "thermal_max_temp_c": (thermal_status.get("detection") or {}).get("max_temp_c"),
            "thermal_ambient_c": (thermal_status.get("detection") or {}).get("ambient_c"),
            "dht_valid": esp32_data.get("dht_valid"),
            "simulation": esp32_data.get("simulation"),
            "lora_ready": esp32_data.get("lora_ready"),
            "last_lora_send_ok": esp32_data.get("last_lora_send_ok"),
            "last_lora_seq": lora_packet.get("seq"),
            "lora_rssi_dbm": lora_packet.get("rssi_dbm"),
            "lora_snr_db": lora_packet.get("snr_db"),
            "lora_pdr_estimate_pct": lora_packet.get("pdr_estimate_pct"),
            "battery_v": ((esp32_data.get("battery_raw") or 0) / 1000.0) if esp32_data.get("battery_raw") else None,
        },
        "chainsaw": {
            "running": chainsaw_status.get("running"),
            "confirmed_detection": chainsaw_status.get("confirmed_detection"),
            "instant_detection": chainsaw_status.get("instant_detection"),
            "score": chainsaw_status.get("score"),
            "rms": chainsaw_status.get("rms"),
            "peak": chainsaw_status.get("peak"),
            "waveform": chainsaw_status.get("waveform"),
            "last_update": chainsaw_status.get("last_update"),
            "alerts_total": chainsaw_status.get("alerts_total"),
            "error": chainsaw_status.get("error"),
            "sample_rate": chainsaw_status.get("sample_rate", 0),
        },
        "camera": cam_status,
        "thermal": thermal_status,
        "lora": lora_packet,
    }
    return data


@app.route("/")
def index():
    if current_role() == "node":
        return render_template("node_dashboard.html")
    return render_template("dashboard.html")


@app.route("/video_feed")
def video_feed_default():
    idx = int(cfg.get("camera_device_index", 0))
    return video_feed_index(idx)


@app.route("/video_feed/<int:device_index>")
def video_feed_index(device_index: int):
    if not bool(cfg.get("camera_enabled", True)):
        return Response("Camera disabled", status=503)
    return Response(cameras.mjpeg_generator(int(device_index)), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/thermal.png")
def thermal_png():
    if not bool(cfg.get("thermal_enabled", False)):
        png = thermal.placeholder_png("Thermal disabled")
    else:
        if not thermal.get_status().get("running"):
            thermal.start()
        png = thermal.get_png() or thermal.placeholder_png("Waiting for MLX90640")
    if not png:
        return Response("Thermal image unavailable", status=503)
    return Response(png, mimetype="image/png")


@app.route("/thermal_feed")
def thermal_feed():
    if not bool(cfg.get("thermal_enabled", False)):
        return Response("Thermal disabled", status=503)
    if not thermal.get_status().get("running"):
        thermal.start()
    return Response(thermal.mjpeg_generator(), mimetype="multipart/x-mixed-replace; boundary=frame")



def _load_font(size: int, bold: bool = False):
    if ImageFont is None:
        return None
    try:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()


def make_sim_video_jpeg(slot: int) -> bytes:
    if Image is None or ImageDraw is None:
        return b""
    width = int(cfg.get("camera_width", 320) or 320)
    height = int(cfg.get("camera_height", 240) or 240)
    width = max(320, min(width, 1280))
    height = max(240, min(height, 720))
    t = time.time()
    img = Image.new("RGB", (width, height), (8, 16, 30))
    draw = ImageDraw.Draw(img)
    title_font = _load_font(30, True)
    small_font = _load_font(18, False)
    tiny_font = _load_font(14, False)
    # Animated background grid.
    offset = int((t * 25 + slot * 20) % 80)
    for x in range(-80 + offset, width, 80):
        draw.line([(x, 0), (x + 120, height)], fill=(18, 38, 68), width=2)
    for y in range(0, height, 60):
        draw.line([(0, y), (width, y)], fill=(14, 30, 54), width=1)
    # Simulated moving subject.
    cx = int(width * (0.25 + 0.50 * ((math.sin(t / 3.0 + slot) + 1) / 2)))
    cy = int(height * (0.45 + 0.18 * math.sin(t / 2.2 + slot)))
    draw.ellipse([(cx - 35, cy - 70), (cx + 35, cy + 70)], outline=(82, 161, 255), width=4)
    draw.rectangle([(cx - 55, cy - 92), (cx + 55, cy + 92)], outline=(255, 255, 255), width=2)
    draw.rectangle([(0, 0), (width, 74)], fill=(0, 0, 0))
    draw.text((18, 10), f"REMOTE NODE {slot} - SIMULATED VIDEO", fill=(255, 255, 255), font=title_font)
    draw.text((18, 45), now_text(), fill=(180, 205, 235), font=small_font)
    badge = "SIMULATION MODE"
    try:
        bbox = draw.textbbox((0, 0), badge, font=small_font)
        bw = bbox[2] - bbox[0] + 24
    except Exception:
        bw = 190
    draw.rounded_rectangle([(width - bw - 18, 16), (width - 18, 56)], radius=12, fill=(176, 114, 20))
    draw.text((width - bw - 6, 25), badge, fill=(255, 255, 255), font=small_font)
    draw.text((18, height - 34), "This is a placeholder stream for testing the main dashboard without remote RPis.", fill=(210, 220, 235), font=tiny_font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=int(cfg.get("camera_jpeg_quality", 55) or 55))
    return buf.getvalue()


@app.route("/sim_node_feed/<int:slot>")
def sim_node_feed(slot: int):
    if slot < 1 or slot > REMOTE_NODE_COUNT:
        return Response("Invalid simulated node slot", status=404)
    def gen():
        while True:
            frame = make_sim_video_jpeg(slot)
            if not frame:
                break
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            time.sleep(1.0 / max(1, int(cfg.get("camera_fps", 10) or 10)))
    return Response(gen(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/node-data")
def api_node_data():
    return jsonify(get_local_node_data(include_alert_update=True))


@app.route("/api/status")
def api_status():
    local = get_local_node_data(include_alert_update=True)
    serial_status = esp32_serial_reader.get_status() if esp32_serial_reader else {}
    local_serial = {
        "enabled": bool(cfg.get("esp32_serial_enabled")),
        "connected": serial_status.get("serial_connected", False) if serial_status else False,
        "port": str(cfg.get("esp32_serial_port", "/dev/ttyUSB0")),
        "error": serial_status.get("serial_error") if serial_status else None,
        "last_packet_time": serial_status.get("last_packet_time") if serial_status else None,
        "packets_by_node": serial_status.get("packets_by_node", {}) if serial_status else {},
        "cache_keys": serial_status.get("cache_keys", []) if serial_status else [],
    }
    return jsonify({
        "ok": True,
        "config": cfg,
        "network": get_network_summary(),
        "local": local,
        "recent_alerts": alert_logger.recent(50),
        "serial": serial_status,
        "local_serial": local_serial,
    })


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    global cfg
    if request.method == "GET":
        return jsonify(cfg)

    data = request.get_json(force=True, silent=True) or {}
    allowed_str = [
        "role", "operation_mode", "selected_esp32_ip", "esp32_scan_prefix", "node_scan_prefix",
        "camera_type", "camera_backend", "camera_fourcc",
        "detection_mode", "audio_browse_start_dir", "log_file",
        "thermal_i2c_address", "wifi_ssid", "wifi_password", "wifi_country", "wifi_interface",
        "esp32_serial_port",
    ]
    allowed_int = [
        "port", "esp32_scan_workers", "camera_device_index", "camera_width", "camera_height", "camera_fps",
        "camera_jpeg_quality", "camera_open_warmup_frames", "sample_rate", "score_threshold", "require_hits", "history_windows",
        "thermal_refresh_rate_hz", "thermal_min_blob_pixels", "thermal_rotate_degrees", "lora_spreading_factor",
        "esp32_serial_baud",
    ]
    allowed_float = [
        "esp32_fetch_timeout", "esp32_scan_timeout", "node_scan_timeout", "node_pull_timeout",
        "server_refresh_sec", "window_sec", "min_rms", "cooldown_sec",
        "thermal_display_min_c", "thermal_display_max_c", "thermal_min_human_temp_c", "thermal_max_human_temp_c",
        "thermal_min_delta_above_ambient_c", "lora_sim_interval_sec", "lora_frequency_mhz", "lora_bandwidth_khz",
    ]
    allowed_bool = ["camera_enabled", "camera_retry_on_failed_read", "auto_start", "thermal_enabled", "thermal_simulation", "thermal_mirror_x", "thermal_mirror_y", "lora_enabled", "event_recording_enabled", "esp32_serial_enabled"]

    for key in allowed_str:
        if key in data:
            value = str(data.get(key) or "").strip()
            if key == "role" and normalize_role(value) not in ("node", "server"):
                value = "server"
            if key == "operation_mode" and value not in ("live", "simulation"):
                value = "live"
            if key == "detection_mode" and value not in ("live", "file"):
                value = "live"
            cfg[key] = value
    for key in allowed_int:
        if key in data:
            try:
                cfg[key] = int(data.get(key))
            except Exception:
                pass
    for key in allowed_float:
        if key in data:
            try:
                cfg[key] = float(data.get(key))
            except Exception:
                pass
    for key in allowed_bool:
        if key in data:
            cfg[key] = bool(data.get(key))

    if "input_device" in data:
        value = data.get("input_device")
        if value in ["", "none", "None", "null", None]:
            cfg["input_device"] = None
        else:
            try:
                cfg["input_device"] = int(value)
            except Exception:
                cfg["input_device"] = value

    if "camera_device_indexes" in data:
        cfg["camera_device_indexes"] = parse_camera_indexes(data.get("camera_device_indexes"), int(cfg.get("camera_device_index", 0)))
        cfg["camera_device_index"] = int(cfg["camera_device_indexes"][0])

    if "remote_node_ips" in data:
        value = data.get("remote_node_ips")
        if isinstance(value, str):
            ips = [x.strip() for x in value.replace(";", ",").replace("\n", ",").split(",") if x.strip()]
        elif isinstance(value, list):
            ips = [str(x).strip() for x in value if str(x).strip()]
        else:
            ips = []
        local_ip = get_primary_ip()
        clean = []
        for ip in ips:
            ip = normalize_ip(ip)
            if ip and ip != local_ip and ip not in clean:
                clean.append(ip)
        cfg["remote_node_ips"] = clean[:REMOTE_NODE_COUNT]
        cfg["remote_node_count"] = REMOTE_NODE_COUNT

    save_config()
    detector.update_config(cfg)

    if bool(cfg.get("camera_enabled", True)):
        cameras.restart_all()
    else:
        cameras.stop_all()

    if bool(cfg.get("thermal_enabled", False)):
        thermal.restart()
    else:
        thermal.stop()

    if cfg.get("detection_mode") == "file":
        detector.stop()

    return jsonify({"ok": True, "config": cfg})


@app.route("/api/wifi-command-preview")
def api_wifi_command_preview():
    ssid = str(cfg.get("wifi_ssid") or "").replace("'", "'\\''")
    password = str(cfg.get("wifi_password") or "").replace("'", "'\\''")
    country = str(cfg.get("wifi_country") or "PH").replace("'", "'\\''")
    iface = str(cfg.get("wifi_interface") or "wlan0").replace("'", "'\\''")
    commands = [
        f"sudo raspi-config nonint do_wifi_country '{country}'",
        f"sudo raspi-config nonint do_wifi_ssid_passphrase '{ssid}' '{password}'",
        f"sudo iw reg set '{country}'",
        f"sudo ip link set '{iface}' down && sudo ip link set '{iface}' up",
        "# If remote connection drops, reboot locally or power-cycle the RPi.",
    ]
    return jsonify({"ok": True, "note": "Commands are not auto-run by the web app to avoid disconnecting your remote session.", "commands": commands})


@app.route("/api/scan-esp32", methods=["POST"])
def api_scan_esp32():
    prefix = get_scan_prefix("esp32")
    found = scan_esp32_devices(
        prefix=prefix,
        timeout=float(cfg.get("esp32_scan_timeout", 0.55)),
        workers=int(cfg.get("esp32_scan_workers", 48)),
    )
    return jsonify({"ok": True, "prefix": prefix, "count": len(found), "devices": found})


@app.route("/api/select-esp32", methods=["POST"])
def api_select_esp32():
    data = request.get_json(force=True, silent=True) or {}
    ip = normalize_ip(str(data.get("ip") or ""))
    if not ip:
        return jsonify({"ok": False, "error": "Missing ESP32 IP"}), 400
    cfg["selected_esp32_ip"] = ip
    save_config()
    return jsonify({"ok": True, "selected_esp32_ip": ip})


@app.route("/api/scan-nodes", methods=["POST"])
def api_scan_nodes():
    prefix = get_scan_prefix("node")
    found = scan_rpi_nodes(
        prefix=prefix,
        port=int(cfg.get("port", 8090)),
        exclude_ips=[get_primary_ip()],
        timeout=float(cfg.get("node_scan_timeout", 0.75)),
    )
    ips = []
    for item in found:
        ip = item.get("rpi_ip") or item.get("ip")
        if ip and ip not in ips and ip != get_primary_ip():
            ips.append(str(ip))
    ips = ips[:REMOTE_NODE_COUNT]
    cfg["remote_node_ips"] = ips
    cfg["remote_node_count"] = REMOTE_NODE_COUNT
    save_config()
    return jsonify({"ok": True, "prefix": prefix, "count": len(found), "nodes": found, "remote_node_ips": ips})


@app.route("/api/server-dashboard")
def api_server_dashboard():
    local = get_local_node_data(include_alert_update=True)
    remote_ips = cfg.get("remote_node_ips") or []
    remote_nodes = build_remote_slots(remote_ips)
    if operation_mode() != "simulation":
        detect_remote_alerts(remote_nodes)
    all_nodes = [local] + remote_nodes
    recent = alert_logger.recent(100)
    if operation_mode() == "simulation":
        recent = simulated_alert_rows(all_nodes) + recent
    return jsonify({
        "ok": True,
        "role": current_role(),
        "operation_mode": operation_mode(),
        "remote_node_count": REMOTE_NODE_COUNT,
        "timestamp": now_text(),
        "local": local,
        "remote_nodes": remote_nodes,
        "all_nodes": all_nodes,
        "lora": lora_simulator.status() if operation_mode() == "simulation" else {"enabled": bool(cfg.get("lora_enabled", True)), "simulation": False},
        "recent_alerts": recent[:100],
    })


@app.route("/api/lora/status")
def api_lora_status():
    if operation_mode() == "simulation":
        get_local_node_data(include_alert_update=False)
        build_remote_slots(cfg.get("remote_node_ips") or [])
        return jsonify({"ok": True, "stored_packet_count": lora_store.count(), **lora_simulator.status()})
    return jsonify({
        "ok": True,
        "enabled": bool(cfg.get("lora_enabled", True)),
        "simulation": False,
        "message": "Real LoRa receiver is not implemented yet. Use simulation mode for packet contract testing.",
    })


@app.route("/api/lora/packets")
def api_lora_packets():
    limit = int(request.args.get("limit", 100))
    return jsonify({"ok": True, "packets": lora_store.recent(limit), "stored_packet_count": lora_store.count()})


@app.route("/api/lora/ingest", methods=["POST"])
def api_lora_ingest():
    packet = request.get_json(force=True, silent=True) or {}
    if not isinstance(packet, dict):
        return jsonify({"ok": False, "error": "Expected JSON object"}), 400
    if not packet.get("timestamp"):
        packet["timestamp"] = now_text()
    packet["received"] = True
    stored = lora_store.record(packet)
    return jsonify({"ok": True, "stored": stored, "packet_id": packet.get("packet_id")})


@app.route("/api/alerts")
def api_alerts():
    limit = int(request.args.get("limit", 100))
    return jsonify({"ok": True, "alerts": alert_logger.recent(limit)})


@app.route("/api/recordings")
def api_recordings():
    limit = int(request.args.get("limit", 50))
    recordings = event_recorder.recent(limit)
    media_root = os.path.join(APP_DIR, "media")
    for rec in recordings:
        urls = []
        for file_path in rec.get("files", []) or []:
            try:
                rel = os.path.relpath(str(file_path), media_root)
                if not rel.startswith(".."):
                    urls.append("/media/" + rel.replace(os.sep, "/"))
            except Exception:
                continue
        rec["file_urls"] = urls
    return jsonify({"ok": True, "recordings": recordings})


@app.route("/media/<path:filename>")
def serve_media(filename):
    return send_from_directory(os.path.join(APP_DIR, "media"), filename)


@app.route("/api/start", methods=["POST"])
def api_start():
    cfg["detection_mode"] = "live"
    save_config()
    detector.update_config(cfg)
    started = detector.start()
    if started:
        time.sleep(0.6)
    status = detector.get_status()
    if started and not status.get("running") and status.get("error"):
        started = False
    return jsonify({"ok": True, "started": started, "status": status})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    stopped = detector.stop()
    return jsonify({"ok": True, "stopped": stopped, "status": detector.get_status()})


@app.route("/api/mode", methods=["POST"])
def api_mode():
    data = request.get_json(force=True, silent=True) or {}
    mode = str(data.get("mode", "live")).strip().lower()
    if mode not in ["live", "file"]:
        return jsonify({"ok": False, "error": "Mode must be live or file"}), 400
    cfg["detection_mode"] = mode
    if "audio_browse_start_dir" in data:
        cfg["audio_browse_start_dir"] = str(data.get("audio_browse_start_dir") or "test_audio")
    save_config()
    detector.update_config(cfg)
    if mode == "file":
        detector.stop()
    return jsonify({"ok": True, "mode": mode, "config": cfg, "status": detector.get_status()})


@app.route("/api/devices")
def api_devices():
    arecord_ok = False
    arecord_missing = False
    arecord_no_devices = False
    arecord_returncode = None
    arecord_stderr_snippet = ""
    live_names = set()
    try:
        proc = subprocess.run(
            ["arecord", "-l"],
            capture_output=True, text=True, timeout=3,
        )
        arecord_returncode = proc.returncode
        arecord_stderr_snippet = (proc.stderr or "")[:200]
        if proc.returncode == 0:
            arecord_ok = True
            for line in proc.stdout.splitlines():
                if line.startswith("card ") and ":" in line:
                    bracket = line.find("[")
                    if bracket > 0:
                        name = line[bracket + 1:].split("]", 1)[0].strip().lower()
                        live_names.add(name)
            # arecord exited 0 but found no cards — also check stderr
            if not live_names:
                combined = (proc.stdout + proc.stderr).lower()
                exit0_markers = ["no audio", "no device", "cannot access", "cannot open"]
                if any(m in combined for m in exit0_markers):
                    arecord_no_devices = True
        else:
            # arecord exited non-zero — check for known no-device indicators
            combined = (proc.stdout + proc.stderr).lower()
            no_dev_markers = [
                "no soundcards found",
                "no soundcard",
                "no capture",
                "no device",
                "cannot access",
                "cannot open audio device",
                "no audio devices",
                "device list error",
            ]
            if any(m in combined for m in no_dev_markers):
                arecord_no_devices = True
    except FileNotFoundError:
        arecord_missing = True
    except Exception:
        pass

    # If arecord reports zero or no capture devices, return empty list.
    # This prevents the stale PortAudio fallback when hardware is truly absent.
    if (arecord_ok and not live_names) or arecord_no_devices:
        meta = {"enumeration_source": "alsa"}
        if arecord_no_devices:
            meta["alsa_status"] = "no_capture_devices"
        else:
            meta["alsa_status"] = "no_capture_lines"
        meta["arecord_returncode"] = arecord_returncode
        meta["arecord_stderr"] = arecord_stderr_snippet
        return jsonify({"ok": True, "devices": [], "meta": meta})

    try:
        import sounddevice as sd
        devices = sd.query_devices()
        data = []
        for idx, dev in enumerate(devices):
            if int(dev.get("max_input_channels", 0)) <= 0:
                continue
            dev_name = str(dev.get("name", f"Device {idx}")).lower()
            if live_names:
                matched = any(lname and lname in dev_name for lname in live_names)
                if not matched:
                    continue
            data.append({
                "id": idx,
                "name": dev.get("name", f"Device {idx}"),
                "max_input_channels": int(dev.get("max_input_channels", 0)),
                "default_samplerate": float(dev.get("default_samplerate", 0)),
            })
        return jsonify({"ok": True, "devices": data, "meta": {"enumeration_source": "alsa+portaudio", "arecord_returncode": arecord_returncode}})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "devices": [], "meta": {"arecord_returncode": arecord_returncode, "error_detail": str(e)}})


@app.route("/api/audio-monitor")
def api_audio_monitor():
    ds = detector.get_status()
    running = bool(ds.get("running"))
    return jsonify({
        "ok": True,
        "running": running,
        "rms": ds.get("rms", 0.0),
        "peak": ds.get("peak", 0.0),
        "score": ds.get("score", 0.0),
        "waveform": ds.get("waveform", []),
        "last_update": ds.get("last_update"),
        "error": ds.get("error"),
        "input_device": ds.get("device"),
        "sample_rate": ds.get("sample_rate", 0),
    })


@app.route("/api/browse")
def api_browse():
    path = resolve_path(request.args.get("path"))
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "Path does not exist", "path": path, "shortcuts": drive_shortcuts(), "supported_exts": list(SUPPORTED_AUDIO_EXTS)}), 404
    if os.path.isfile(path):
        path = os.path.dirname(path)
    dirs: List[Dict[str, str]] = []
    files: List[Dict[str, Any]] = []
    try:
        for name in sorted(os.listdir(path), key=lambda s: s.lower()):
            full = os.path.join(path, name)
            try:
                if os.path.isdir(full):
                    dirs.append({"name": name, "path": full})
                elif os.path.isfile(full) and is_supported_audio(full):
                    try:
                        size_mb = round(os.path.getsize(full) / (1024 * 1024), 2)
                    except Exception:
                        size_mb = None
                    files.append({"name": name, "path": full, "size_mb": size_mb, "ext": os.path.splitext(name)[1].lower()})
            except (PermissionError, OSError):
                continue
    except PermissionError:
        return jsonify({"ok": False, "error": "Permission denied for this folder", "path": path, "parent": os.path.dirname(path) if path != "/" else "/", "shortcuts": drive_shortcuts(), "supported_exts": list(SUPPORTED_AUDIO_EXTS)}), 403
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "path": path, "shortcuts": drive_shortcuts(), "supported_exts": list(SUPPORTED_AUDIO_EXTS)}), 500
    return jsonify({"ok": True, "path": path, "parent": os.path.dirname(path) if path != "/" else "/", "dirs": dirs, "files": files, "shortcuts": drive_shortcuts(), "supported_exts": list(SUPPORTED_AUDIO_EXTS)})


@app.route("/api/audio")
def api_audio():
    path = resolve_path(request.args.get("path"))
    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": "Audio file not found"}), 404
    if not is_supported_audio(path):
        return jsonify({"ok": False, "error": "Unsupported audio file"}), 400
    return send_file(path, conditional=True)


@app.route("/api/test-files")
def api_test_files():
    files = []
    if os.path.isdir(TEST_AUDIO_DIR):
        for name in sorted(os.listdir(TEST_AUDIO_DIR)):
            if is_supported_audio(name):
                files.append(name)
    return jsonify({"ok": True, "files": files})


@app.route("/test_audio/<path:filename>")
def serve_test_audio(filename):
    return send_from_directory(TEST_AUDIO_DIR, filename)


@app.route("/api/analyze-file", methods=["POST"])
def api_analyze_file():
    data = request.get_json(force=True, silent=True) or {}
    if data.get("path"):
        path = resolve_path(str(data.get("path")))
    else:
        filename = os.path.basename(str(data.get("filename", "")))
        if not filename:
            return jsonify({"ok": False, "error": "No audio file path provided"}), 400
        path = os.path.join(TEST_AUDIO_DIR, filename)
    if not os.path.exists(path):
        return jsonify({"ok": False, "error": "File not found"}), 404
    if not os.path.isfile(path):
        return jsonify({"ok": False, "error": "Selected path is not a file"}), 400
    if not is_supported_audio(path):
        return jsonify({"ok": False, "error": "Unsupported audio file. Supported: WAV, MP3, M4A, AAC, FLAC, OGG"}), 400
    cfg["detection_mode"] = "file"
    cfg["audio_browse_start_dir"] = os.path.dirname(path)
    save_config()
    detector.update_config(cfg)
    detector.stop()
    try:
        result = analyze_audio_file(path, cfg)
        if result.get("confirmed"):
            alert_logger.log(local_node_name(), "Audio File Test", "CHAINSAW", "TEST", f"Chainsaw-like sound detected in file: {os.path.basename(path)}", json.dumps(result)[:2000])
        return jsonify({"ok": True, "mode": "file", "result": result, "config": cfg})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=str(cfg.get("host", "0.0.0.0")))
    parser.add_argument("--port", type=int, default=int(cfg.get("port", 8090)))
    args = parser.parse_args()

    cfg["host"] = args.host
    cfg["port"] = args.port
    save_config()

    if not is_port_available(args.host, args.port):
        print("")
        print("FireNode RPi Unified Main Server / Node Web GUI")
        print(f"ERROR: Port {args.port} is already in use, so this copy of the server was not started.")
        print("Most likely an older FireNode server is still running or a systemd service is active.")
        print("Try opening the existing server first:")
        urls = get_lan_urls(args.port)
        if urls:
            for url in urls:
                print(f"  {url}")
        else:
            print(f"  http://<this-rpi-ip>:{args.port}")
        print("")
        print("To stop the old server, run:")
        print("  ./stop_server.sh")
        print("Then start again:")
        print("  ./run.sh")
        print("")
        sys.exit(98)

    if bool(cfg.get("camera_enabled", True)):
        cameras.start_all()
    if bool(cfg.get("thermal_enabled", False)):
        thermal.start()
    if bool(cfg.get("auto_start", True)) and cfg.get("detection_mode", "live") == "live":
        detector.start()

    global esp32_serial_reader
    if cfg.get("esp32_serial_enabled"):
        port = str(cfg.get("esp32_serial_port", "/dev/ttyUSB0"))
        esp32_serial_reader = ESP32SerialReader(
            port=port,
            baud=int(cfg.get("esp32_serial_baud", 115200)),
            enabled=True,
        )
        esp32_serial_reader.start()
        print(f"ESP32 serial reader started on {port} @ {cfg.get('esp32_serial_baud')}")

    print("")
    print("FireNode RPi Unified Main Server / Node Web GUI")
    print(f"Role: {current_role()}")
    print(f"Mode: {operation_mode()}")
    print(f"Remote node slots: {REMOTE_NODE_COUNT}")
    urls = get_lan_urls(args.port)
    if urls:
        print("Open from another device on the same Wi-Fi/LAN:")
        for url in urls:
            print(f"  {url}")
    else:
        print(f"Open: http://<raspberry-pi-ip>:{args.port}")
    print(f"Local: http://127.0.0.1:{args.port}")
    print("Node API: /api/node-data")
    print("Camera: /video_feed/<index>")
    print("Thermal: /thermal_feed")
    print("Press CTRL+C to stop.")
    print("")
    app.run(host=args.host, port=args.port, threaded=True)


if __name__ == "__main__":
    main()
