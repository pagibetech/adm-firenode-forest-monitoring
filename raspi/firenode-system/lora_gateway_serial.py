#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from datetime import datetime
from typing import Any, Dict

try:
    import serial
except Exception:  # pragma: no cover
    serial = None


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def post_packet(api_base: str, packet: Dict[str, Any], timeout: float = 3.0) -> Dict[str, Any]:
    url = api_base.rstrip("/") + "/api/lora/ingest"
    body = json.dumps(packet).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8"))


def parse_gateway_line(line: str) -> Dict[str, Any]:
    packet = json.loads(line)
    if not isinstance(packet, dict):
        raise ValueError("Gateway line must be a JSON object")
    if packet.get("gateway_status") and not packet.get("payload"):
        return {}
    if not packet.get("node_id") and not packet.get("payload"):
        return {}
    packet.setdefault("timestamp", now_text())
    packet.setdefault("received", True)
    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Read LoRa gateway JSON packets from serial and post them to FireNode.")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port connected to ESP32/SX127x gateway.")
    parser.add_argument("--baud", type=int, default=115200, help="Serial baud rate.")
    parser.add_argument("--api-base", default="http://127.0.0.1:8090", help="FireNode web app base URL.")
    parser.add_argument("--timeout", type=float, default=3.0, help="HTTP post timeout in seconds.")
    args = parser.parse_args()

    if serial is None:
        print("pyserial is not installed. Install it with: pip install pyserial", file=sys.stderr)
        return 2

    print(f"Opening LoRa gateway serial port {args.port} @ {args.baud}")
    print(f"Posting packets to {args.api_base.rstrip('/')}/api/lora/ingest")
    with serial.Serial(args.port, args.baud, timeout=1.0) as ser:
        while True:
            raw = ser.readline()
            if not raw:
                continue
            line = raw.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                packet = parse_gateway_line(line)
                if not packet:
                    print(f"{now_text()} gateway_status={line[:120]}")
                    continue
                result = post_packet(args.api_base, packet, timeout=args.timeout)
                print(f"{now_text()} stored={result.get('stored')} packet_id={result.get('packet_id')}")
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                print(f"{now_text()} gateway line failed: {exc} | raw={line[:160]}", file=sys.stderr)
                time.sleep(0.1)


if __name__ == "__main__":
    raise SystemExit(main())
