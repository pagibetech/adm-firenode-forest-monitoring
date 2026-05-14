#!/usr/bin/env python3
from __future__ import annotations

import os
import socket
import subprocess
from typing import Dict, List, Optional


def get_primary_ip() -> str:
    """Return the most likely LAN IP of this Raspberry Pi."""
    # This does not send packets; it asks the kernel which source IP would be used.
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    try:
        out = subprocess.check_output(["hostname", "-I"], text=True, timeout=1.0, stderr=subprocess.DEVNULL).strip()
        for token in out.split():
            if token and not token.startswith("127.") and "." in token:
                return token
    except Exception:
        pass

    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass

    return "127.0.0.1"


def node_name_from_ip(ip: Optional[str] = None) -> str:
    ip = ip or get_primary_ip()
    return "FireNode-" + str(ip).replace(".", "-")


def subnet_prefix_from_ip(ip: Optional[str] = None) -> str:
    ip = ip or get_primary_ip()
    parts = str(ip).split(".")
    if len(parts) >= 3:
        return ".".join(parts[:3])
    return "192.168.1"


def hosts_in_subnet(prefix: Optional[str] = None, start: int = 1, end: int = 254) -> List[str]:
    prefix = prefix or subnet_prefix_from_ip()
    start = max(1, int(start))
    end = min(254, int(end))
    return [f"{prefix}.{i}" for i in range(start, end + 1)]


def get_network_summary() -> Dict[str, str]:
    ip = get_primary_ip()
    return {
        "rpi_ip": ip,
        "node_name": node_name_from_ip(ip),
        "subnet_prefix": subnet_prefix_from_ip(ip),
    }
