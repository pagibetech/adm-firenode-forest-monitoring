#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional


class AlertLogger:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def _init_db(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    node_name TEXT,
                    source TEXT,
                    event_type TEXT,
                    severity TEXT,
                    message TEXT,
                    details TEXT
                )
                """
            )
            con.commit()

    def log(self, node_name: str, source: str, event_type: str, severity: str, message: str, details: str = "") -> None:
        with self.lock:
            with self._connect() as con:
                con.execute(
                    "INSERT INTO alerts(timestamp,node_name,source,event_type,severity,message,details) VALUES(?,?,?,?,?,?,?)",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), node_name, source, event_type, severity, message, details),
                )
                con.commit()

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(500, int(limit)))
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]
