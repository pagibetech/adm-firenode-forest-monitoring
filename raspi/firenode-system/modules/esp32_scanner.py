#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from .esp32_client import fetch_esp32_data, looks_like_firenode_esp32
from .network_utils import hosts_in_subnet, subnet_prefix_from_ip


def _probe(ip: str, timeout: float) -> Optional[Dict[str, Any]]:
    res = fetch_esp32_data(ip, timeout=timeout)
    if not res.get("ok"):
        return None
    data = res.get("data") or {}
    if not looks_like_firenode_esp32(data):
        return None
    return {
        "ip": ip,
        "url": res.get("url"),
        "node_id": data.get("node_id") or data.get("id") or f"ESP32-{ip}",
        "temperature": data.get("temperature"),
        "humidity": data.get("humidity"),
        "smoke_detected": data.get("smoke_detected"),
        "human_detected": data.get("human_detected"),
        "rssi": data.get("rssi"),
        "raw": data,
        "elapsed_ms": res.get("elapsed_ms"),
    }


def scan_esp32_devices(prefix: Optional[str] = None, timeout: float = 0.55, workers: int = 48) -> List[Dict[str, Any]]:
    prefix = prefix or subnet_prefix_from_ip()
    ips = hosts_in_subnet(prefix)
    found: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futures = {ex.submit(_probe, ip, timeout): ip for ip in ips}
        for fut in as_completed(futures):
            item = fut.result()
            if item:
                found.append(item)
    found.sort(key=lambda x: tuple(int(p) for p in str(x["ip"]).split(".")))
    return found
