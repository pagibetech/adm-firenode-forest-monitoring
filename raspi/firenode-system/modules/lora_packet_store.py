#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List


class LoraPacketStore:
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
                CREATE TABLE IF NOT EXISTS lora_packets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    packet_id TEXT NOT NULL UNIQUE,
                    rx_ts TEXT NOT NULL,
                    node_id TEXT,
                    node_name TEXT,
                    slot INTEGER,
                    seq INTEGER,
                    rssi_dbm REAL,
                    snr_db REAL,
                    pdr_estimate_pct REAL,
                    frequency_mhz REAL,
                    payload_json TEXT NOT NULL,
                    raw_json TEXT NOT NULL,
                    accepted INTEGER NOT NULL DEFAULT 1
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_lora_packets_node_seq ON lora_packets(node_id, seq)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_lora_packets_rx_ts ON lora_packets(rx_ts)")
            con.commit()

    def record(self, packet: Dict[str, Any]) -> bool:
        packet_id = str(packet.get("packet_id") or "").strip()
        if not packet_id:
            node_id = str(packet.get("node_id") or packet.get("node_name") or "unknown")
            seq = packet.get("seq", 0)
            packet_id = f"{node_id}-{seq}-{int(datetime.now().timestamp())}"
            packet["packet_id"] = packet_id
        payload = packet.get("payload") if isinstance(packet.get("payload"), dict) else {}
        with self.lock:
            with self._connect() as con:
                cur = con.execute(
                    """
                    INSERT OR IGNORE INTO lora_packets(
                        packet_id, rx_ts, node_id, node_name, slot, seq, rssi_dbm, snr_db,
                        pdr_estimate_pct, frequency_mhz, payload_json, raw_json, accepted
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        packet_id,
                        str(packet.get("timestamp") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        packet.get("node_id"),
                        packet.get("node_name"),
                        packet.get("slot"),
                        packet.get("seq"),
                        packet.get("rssi_dbm"),
                        packet.get("snr_db"),
                        packet.get("pdr_estimate_pct"),
                        packet.get("frequency_mhz"),
                        json.dumps(payload, separators=(",", ":"), sort_keys=True),
                        json.dumps(packet, separators=(",", ":"), sort_keys=True),
                        1 if packet.get("received", True) else 0,
                    ),
                )
                con.commit()
                return cur.rowcount > 0

    def recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        limit = max(1, min(1000, int(limit)))
        with self._connect() as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("SELECT * FROM lora_packets ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            data: List[Dict[str, Any]] = []
            for row in rows:
                item = dict(row)
                try:
                    item["payload"] = json.loads(item.pop("payload_json") or "{}")
                except Exception:
                    item["payload"] = {}
                try:
                    item["raw"] = json.loads(item.pop("raw_json") or "{}")
                except Exception:
                    item["raw"] = {}
                data.append(item)
            return data

    def count(self) -> int:
        with self._connect() as con:
            row = con.execute("SELECT COUNT(*) FROM lora_packets").fetchone()
            return int(row[0] if row else 0)
