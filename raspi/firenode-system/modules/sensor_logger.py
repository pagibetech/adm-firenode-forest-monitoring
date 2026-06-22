#!/usr/bin/env python3
"""Sensor data logger -- ESP32 sensor readings stored in SQLite with configurable interval."""

from __future__ import annotations

import os
import sqlite3
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    node_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    smoke INTEGER,
    smoke_detected INTEGER,
    pir INTEGER,
    human_detected INTEGER,
    battery_raw INTEGER,
    seq INTEGER
);
CREATE INDEX IF NOT EXISTS idx_sensor_logs_node ON sensor_logs(node_name);
CREATE INDEX IF NOT EXISTS idx_sensor_logs_time ON sensor_logs(timestamp);
"""


class SensorLogger:
    """Background logger that periodically writes ESP32 sensor data to SQLite."""

    def __init__(self, db_path: str, get_config: Callable[[], Dict[str, Any]],
                 get_esp32_func: Optional[Callable[[], Optional[Dict[str, Any]]]] = None):
        self.db_path = db_path
        self.get_config = get_config
        self.get_esp32_func = get_esp32_func
        self.lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._init_db()

    def set_esp32_provider(self, func: Callable[[], Optional[Dict[str, Any]]]) -> None:
        self.get_esp32_func = func

    def _init_db(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="sensor-logger")
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                cfg = self.get_config()
                interval = int(cfg.get("sensor_log_interval_sec", 60))
                if interval > 0:
                    self._log_current_sensors()
            except Exception:
                pass
            interval = int(self.get_config().get("sensor_log_interval_sec", 60))
            if interval <= 0:
                self._stop_event.wait(timeout=5)
            else:
                self._stop_event.wait(timeout=max(interval, 5))

    def _log_current_sensors(self) -> None:
        if self.get_esp32_func is None:
            return
        esp32_data = self.get_esp32_func()
        if not esp32_data:
            return

        from modules.network_utils import node_name_from_ip, get_primary_ip
        node_name = node_name_from_ip(get_primary_ip())
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        with self._conn() as conn:
            conn.execute(
                """INSERT INTO sensor_logs
                   (node_name, timestamp, temperature, humidity, smoke,
                    smoke_detected, pir, human_detected, battery_raw, seq)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node_name,
                    now,
                    esp32_data.get("temperature"),
                    esp32_data.get("humidity"),
                    esp32_data.get("smoke"),
                    1 if esp32_data.get("smoke_detected") else 0,
                    esp32_data.get("pir", 0),
                    1 if esp32_data.get("human_detected") else 0,
                    esp32_data.get("battery_raw"),
                    esp32_data.get("seq"),
                ),
            )

    def log_now(self, esp32_data: Dict[str, Any]) -> None:
        """Directly write a row from external caller (for nodes with serial ESP32)."""
        from modules.network_utils import node_name_from_ip, get_primary_ip
        node_name = node_name_from_ip(get_primary_ip())
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO sensor_logs
                   (node_name, timestamp, temperature, humidity, smoke,
                    smoke_detected, pir, human_detected, battery_raw, seq)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    node_name,
                    now,
                    esp32_data.get("temperature"),
                    esp32_data.get("humidity"),
                    esp32_data.get("smoke"),
                    1 if esp32_data.get("smoke_detected") else 0,
                    esp32_data.get("pir", 0),
                    1 if esp32_data.get("human_detected") else 0,
                    esp32_data.get("battery_raw"),
                    esp32_data.get("seq"),
                ),
            )

    def query(
        self,
        node_name: Optional[str] = None,
        since: Optional[str] = None,
        until: Optional[str] = None,
        sort: str = "desc",
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        where_clauses: List[str] = []
        params: List[Any] = []

        if node_name:
            where_clauses.append("node_name = ?")
            params.append(node_name)
        if since:
            where_clauses.append("timestamp >= ?")
            params.append(since)
        if until:
            where_clauses.append("timestamp <= ?")
            params.append(until)

        where = ""
        if where_clauses:
            where = " WHERE " + " AND ".join(where_clauses)

        order = "DESC" if sort.lower() == "desc" else "ASC"

        with self._conn() as conn:
            count_row = conn.execute(f"SELECT COUNT(*) FROM sensor_logs{where}", params).fetchone()
            total = count_row[0] if count_row else 0
            rows = conn.execute(
                f"SELECT * FROM sensor_logs{where} ORDER BY id {order} LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()

        return [dict(r) for r in rows], total

    def get_nodes(self) -> List[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT node_name FROM sensor_logs ORDER BY node_name"
            ).fetchall()
        return [r["node_name"] for r in rows]
