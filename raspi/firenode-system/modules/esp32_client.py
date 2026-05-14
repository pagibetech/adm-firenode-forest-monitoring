#!/usr/bin/env python3
from __future__ import annotations

import time
from typing import Any, Dict, Optional

import requests


def normalize_ip(ip: str) -> str:
    ip = str(ip or "").strip()
    ip = ip.replace("http://", "").replace("https://", "")
    ip = ip.split("/")[0]
    return ip


def esp32_data_url(ip: str) -> str:
    return f"http://{normalize_ip(ip)}/data"


def fetch_esp32_data(ip: str, timeout: float = 1.0) -> Dict[str, Any]:
    ip = normalize_ip(ip)
    if not ip:
        return {"ok": False, "error": "No ESP32 IP selected", "ip": ""}
    url = esp32_data_url(ip)
    started = time.time()
    try:
        r = requests.get(url, timeout=float(timeout))
        elapsed_ms = int((time.time() - started) * 1000)
        if r.status_code != 200:
            return {"ok": False, "ip": ip, "url": url, "status_code": r.status_code, "error": "HTTP error", "elapsed_ms": elapsed_ms}
        data = r.json()
        if not isinstance(data, dict):
            return {"ok": False, "ip": ip, "url": url, "error": "JSON is not an object", "elapsed_ms": elapsed_ms}
        data["_source_ip"] = ip
        data["_source_url"] = url
        data["_fetch_ok"] = True
        data["_elapsed_ms"] = elapsed_ms
        return {"ok": True, "ip": ip, "url": url, "data": data, "elapsed_ms": elapsed_ms}
    except Exception as e:
        return {"ok": False, "ip": ip, "url": url, "error": str(e)}


def looks_like_firenode_esp32(data: Dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return False
    # The user's ESP32 /data JSON has these keys. Keep validation broad so future firmware still works.
    keys = set(data.keys())
    required_any = {"temperature", "humidity", "smoke", "smoke_detected", "pir", "human_detected", "node_id"}
    return bool(keys.intersection(required_any)) and ("node_id" in keys or "temperature" in keys or "humidity" in keys)
