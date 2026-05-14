#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional


class EventRecorder:
    def __init__(self, media_dir: str, get_config: Callable[[], Dict[str, Any]]):
        self.media_dir = Path(media_dir)
        self.get_config = get_config
        self.lock = threading.Lock()
        self.media_dir.mkdir(parents=True, exist_ok=True)

    def _safe_name(self, text: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", text.strip())
        return cleaned.strip("-") or "event"

    def _event_dir(self, node_name: str, event_type: str) -> Path:
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = f"{ts}-{self._safe_name(node_name)}-{self._safe_name(event_type)}"
        path = self.media_dir / "events" / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def record_snapshot_event(
        self,
        node_name: str,
        event_type: str,
        details: Dict[str, Any],
        frame_jpeg: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        if not bool(self.get_config().get("event_recording_enabled", True)):
            return {"ok": False, "skipped": True, "reason": "event recording disabled"}

        with self.lock:
            event_dir = self._event_dir(node_name, event_type)
            metadata = {
                "ok": True,
                "event_type": event_type,
                "node_name": node_name,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": details,
                "files": [],
            }

            if frame_jpeg:
                frame_path = event_dir / "camera0.jpg"
                frame_path.write_bytes(frame_jpeg)
                metadata["files"].append(str(frame_path))

            metadata_path = event_dir / "metadata.json"
            metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            metadata["metadata_path"] = str(metadata_path)
            metadata["event_dir"] = str(event_dir)
            return metadata

    def recent(self, limit: int = 50) -> list[Dict[str, Any]]:
        limit = max(1, min(200, int(limit)))
        root = self.media_dir / "events"
        if not root.exists():
            return []
        rows: list[Dict[str, Any]] = []
        for metadata_path in sorted(root.glob("*/metadata.json"), reverse=True)[:limit]:
            try:
                item = json.loads(metadata_path.read_text(encoding="utf-8"))
                item.setdefault("metadata_path", str(metadata_path))
                item.setdefault("event_dir", str(metadata_path.parent))
                rows.append(item)
            except Exception:
                continue
        return rows
