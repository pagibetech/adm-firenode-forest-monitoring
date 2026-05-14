#!/usr/bin/env python3
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Sequence, Set

import requests

from .network_utils import get_primary_ip, hosts_in_subnet, subnet_prefix_from_ip


def fetch_node_data(ip: str, port: int = 8090, timeout: float = 1.0) -> Dict[str, Any]:
    url = f"http://{ip}:{int(port)}/api/node-data"
    try:
        r = requests.get(url, timeout=float(timeout))
        if r.status_code != 200:
            return {"online": False, "ip": ip, "url": url, "error": f"HTTP {r.status_code}"}
        data = r.json()
        if not isinstance(data, dict) or not data.get("firenode_api"):
            return {"online": False, "ip": ip, "url": url, "error": "Not a FireNode API"}
        data["online"] = True
        data["url"] = url
        return data
    except Exception as e:
        return {"online": False, "ip": ip, "url": url, "error": str(e)}


def scan_rpi_nodes(prefix: Optional[str] = None, port: int = 8090, exclude_ips: Optional[Sequence[str]] = None,
                   timeout: float = 0.75, workers: int = 48) -> List[Dict[str, Any]]:
    prefix = prefix or subnet_prefix_from_ip()
    exclude: Set[str] = set(exclude_ips or [])
    exclude.add(get_primary_ip())
    ips = [ip for ip in hosts_in_subnet(prefix) if ip not in exclude]
    found: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(workers))) as ex:
        futures = {ex.submit(fetch_node_data, ip, port, timeout): ip for ip in ips}
        for fut in as_completed(futures):
            data = fut.result()
            if data.get("online") and data.get("firenode_api"):
                found.append(data)
    found.sort(key=lambda x: tuple(int(p) for p in str(x.get("rpi_ip") or x.get("ip") or "0.0.0.0").split(".")))
    return found


def pull_nodes(ips: Sequence[str], port: int = 8090, timeout: float = 1.2, workers: int = 12) -> List[Dict[str, Any]]:
    clean_ips = []
    for ip in ips:
        ip = str(ip or "").strip()
        if ip and ip not in clean_ips:
            clean_ips.append(ip)
    results: List[Dict[str, Any]] = []
    if not clean_ips:
        return results
    with ThreadPoolExecutor(max_workers=max(1, min(int(workers), len(clean_ips)))) as ex:
        futures = {ex.submit(fetch_node_data, ip, port, timeout): ip for ip in clean_ips}
        for fut in as_completed(futures):
            results.append(fut.result())
    results.sort(key=lambda x: str(x.get("node_name") or x.get("ip") or x.get("rpi_ip") or ""))
    return results
