#!/usr/bin/env python3
"""ESP32 USB serial reader for MAIN RPi dashboard.

Reads lines from /dev/ttyUSB0 at 115200, parses sensor packets, and caches
the latest data per node ID in a thread-safe manner.

Expected serial line formats:
  [RECEIVED] NODE=NODE_01,SEQ=1765,TEMP=27.20,HUM=63.20,PIR=0,MQ=2095,BAT=2926
  [LORA TX OK] NODE=MAIN,SEQ=1765,TEMP=27.70,HUM=62.90,PIR=0,MQ=356,BAT=0

Decorative/log lines (e.g., ===== LORA RX =====, [RSSI] -38) are ignored.
"""
from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

try:
    import serial
except Exception:  # pragma: no cover
    serial = None


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


class ESP32SerialReader:
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baud: int = 115200,
        enabled: bool = True,
    ):
        self.port = port
        self.baud = baud
        self.enabled = enabled
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.serial_connected = False
        self.serial_error: Optional[str] = None
        self.last_packet_time: Optional[str] = None
        self.packets_by_node: Dict[str, int] = {}
        self._last_rssi: Optional[float] = None
        self._last_snr: Optional[float] = None

    def start(self) -> None:
        if not self.enabled:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    @staticmethod
    def parse_line(line: str, rssi: Optional[float] = None, snr: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Parse a single serial line and return a dict if it contains sensor data."""
        if "NODE=" not in line:
            return None
        start = line.index("NODE=")
        payload = line[start:]
        data: Dict[str, Any] = {}
        for part in payload.split(","):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.strip().upper()
            value = value.strip()
            if key == "NODE":
                data["node_id"] = value
            elif key == "SEQ":
                data["seq"] = _safe_int(value)
            elif key == "TEMP":
                data["temperature"] = _safe_float(value)
            elif key == "HUM":
                data["humidity"] = _safe_float(value)
            elif key == "PIR":
                data["pir"] = _safe_int(value)
            elif key == "MQ":
                data["mq"] = _safe_int(value)
            elif key == "BAT":
                data["bat"] = _safe_int(value)
            elif key == "RSSI":
                data["rssi_dbm"] = _safe_float(value)
            elif key == "SNR":
                data["snr_db"] = _safe_float(value)
        if rssi is not None:
            data["rssi_dbm"] = rssi
        if snr is not None:
            data["snr_db"] = snr
        if not data.get("node_id"):
            return None
        return data

    def _run(self) -> None:
        if serial is None:
            self.serial_error = "pyserial is not installed"
            return
        while not self._stop_event.is_set():
            try:
                with serial.Serial(self.port, self.baud, timeout=1.0) as ser:
                    self.serial_connected = True
                    self.serial_error = None
                    while not self._stop_event.is_set():
                        raw = ser.readline()
                        if not raw:
                            continue
                        line = raw.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        import re
                        # Try to parse this line as a sensor data packet
                        parsed = self.parse_line(line, self._last_rssi, self._last_snr)
                        if parsed:
                            node_id = str(parsed.get("node_id") or "unknown")
                            self.last_packet_time = now_text()
                            with self._lock:
                                self._cache[node_id] = parsed
                                self.packets_by_node[node_id] = (
                                    self.packets_by_node.get(node_id, 0) + 1
                                )
                                # Store the last cached node_id for RSSI/SNR association
                                self._last_cached_node_id = node_id
                        # Track RSSI/SNR and apply to the last cached packet
                        rssi_m = re.search(r'\[RSSI\]\s*(-?[\d.]+)', line)
                        if rssi_m:
                            rssi_val = float(rssi_m.group(1))
                            self._last_rssi = rssi_val
                            # Apply to last cached node
                            if hasattr(self, '_last_cached_node_id') and self._last_cached_node_id:
                                with self._lock:
                                    cached = self._cache.get(self._last_cached_node_id)
                                    if cached:
                                        cached['rssi_dbm'] = rssi_val
                        snr_m = re.search(r'\[SNR\]\s*(-?[\d.]+)', line)
                        if snr_m:
                            snr_val = float(snr_m.group(1))
                            self._last_snr = snr_val
                            # Apply to last cached node
                            if hasattr(self, '_last_cached_node_id') and self._last_cached_node_id:
                                with self._lock:
                                    cached = self._cache.get(self._last_cached_node_id)
                                    if cached:
                                        cached['snr_db'] = snr_val
            except Exception as exc:
                self.serial_connected = False
                self.serial_error = str(exc)
                time.sleep(2.0)

    def get_cache(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._cache)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "serial_connected": self.serial_connected,
                "serial_error": self.serial_error,
                "last_packet_time": self.last_packet_time,
                "packets_by_node": dict(self.packets_by_node),
                "cache_keys": list(self._cache.keys()),
            }


def serial_data_to_esp32_format(serial_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a parsed serial packet dict into the esp32_data shape used by the dashboard."""
    temp = serial_data.get("temperature")
    hum = serial_data.get("humidity")
    pir = serial_data.get("pir")
    mq = serial_data.get("mq")
    bat = serial_data.get("bat")
    return {
        "node_id": serial_data.get("node_id", "UNKNOWN"),
        "temperature": temp,
        "humidity": hum,
        "smoke": mq,
        "smoke_ppm": mq,
        "smoke_detected": False,  # Threshold logic can be added later
        "pir": pir,
        "human_detected": bool(pir),
        "dht_valid": temp is not None and hum is not None,
        "lora_ready": True,
        "last_lora_send_ok": True,
        "seq": serial_data.get("seq"),
        "battery_raw": bat,
    }


def sensor_summary_from_serial(serial_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build a sensor_summary dict compatible with dashboard cards."""
    esp = serial_data_to_esp32_format(serial_data)
    return {
        "temperature": esp.get("temperature"),
        "humidity": esp.get("humidity"),
        "smoke_raw": esp.get("smoke"),
        "smoke_detected": bool(esp.get("smoke_detected", False)),
        "pir_raw": esp.get("pir"),
        "human_detected": bool(esp.get("human_detected", False)),
        "thermal_human_detected": False,
        "thermal_max_temp_c": None,
        "thermal_ambient_c": None,
        "dht_valid": esp.get("dht_valid"),
        "simulation": False,
        "lora_ready": True,
        "last_lora_send_ok": True,
        "last_lora_seq": esp.get("seq"),
        "lora_rssi_dbm": serial_data.get("rssi_dbm"),
        "lora_snr_db": serial_data.get("snr_db"),
        "battery_v": (serial_data.get("bat") / 1000.0) if isinstance(serial_data.get("bat"), int) else None,
    }
