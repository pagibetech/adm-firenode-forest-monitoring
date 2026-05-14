#!/usr/bin/env python3
from __future__ import annotations

import math
import time
from collections import deque
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional


class LoraPacketSimulator:
    """Stateful LoRa receiver simulation for dashboard and API development."""

    def __init__(self, get_config: Callable[[], Dict[str, Any]], max_history: int = 240):
        self.get_config = get_config
        self.max_history = int(max_history)
        self.history: Deque[Dict[str, Any]] = deque(maxlen=self.max_history)
        self.latest_by_slot: Dict[int, Dict[str, Any]] = {}
        self.seq_by_slot: Dict[int, int] = {}
        self.last_emit_by_slot: Dict[int, float] = {}

    def _interval_sec(self) -> float:
        cfg = self.get_config()
        try:
            return max(1.0, float(cfg.get("lora_sim_interval_sec", 5.0)))
        except Exception:
            return 5.0

    def _now_text(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _node_id(self, slot: int, node_name: str) -> str:
        if slot <= 0:
            return "MAIN-CENTER"
        return f"REMOTE-{slot:02d}"

    def _make_link_metrics(self, slot: int, seq: int) -> Dict[str, Any]:
        phase = time.time() / 11.0 + slot * 0.73 + seq * 0.17
        rssi = -53.0 - slot * 6.5 + 2.5 * math.sin(phase)
        snr = 9.5 - slot * 0.9 + 1.2 * math.cos(phase / 1.7)
        pdr = 98.0 - slot * 3.0 - max(0.0, abs(rssi) - 80.0) * 0.4
        return {
            "rssi_dbm": round(rssi, 1),
            "snr_db": round(snr, 1),
            "pdr_estimate_pct": round(max(70.0, min(99.5, pdr)), 1),
        }

    def packet_for_node(
        self,
        slot: int,
        node_name: str,
        esp32_data: Dict[str, Any],
        chainsaw_status: Optional[Dict[str, Any]] = None,
        thermal_status: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        slot = int(slot)
        now = time.time()
        latest = self.latest_by_slot.get(slot)
        if latest and (now - float(self.last_emit_by_slot.get(slot, 0))) < self._interval_sec():
            return latest

        seq = int(self.seq_by_slot.get(slot, 0)) + 1
        self.seq_by_slot[slot] = seq
        metrics = self._make_link_metrics(slot, seq)
        chainsaw_status = chainsaw_status or {}
        thermal_detection = (thermal_status or {}).get("detection") or {}
        payload = {
            "node_id": self._node_id(slot, node_name),
            "node_name": node_name,
            "temperature_c": esp32_data.get("temperature"),
            "humidity_pct": esp32_data.get("humidity"),
            "smoke_ppm": esp32_data.get("smoke_ppm", esp32_data.get("smoke")),
            "smoke_detected": bool(esp32_data.get("smoke_detected", False)),
            "pir_human": bool(esp32_data.get("human_detected", False)),
            "chainsaw_detected": bool(chainsaw_status.get("confirmed_detection", False)),
            "chainsaw_score": chainsaw_status.get("score"),
            "thermal_human": bool(thermal_detection.get("human_detected", False)),
            "thermal_max_temp_c": thermal_detection.get("max_temp_c"),
            "battery_v": round(12.4 - slot * 0.07 + 0.08 * math.sin(now / 30.0 + slot), 2),
        }
        packet = {
            "packet_id": f"SIM-LORA-{slot}-{seq}",
            "simulation": True,
            "received": True,
            "timestamp": self._now_text(),
            "slot": slot,
            "node_id": payload["node_id"],
            "node_name": node_name,
            "seq": seq,
            "frequency_mhz": float(self.get_config().get("lora_frequency_mhz", 433.0)),
            "spreading_factor": int(self.get_config().get("lora_spreading_factor", 7)),
            "bandwidth_khz": float(self.get_config().get("lora_bandwidth_khz", 125.0)),
            **metrics,
            "payload": payload,
            "alerts": {
                "smoke": payload["smoke_detected"],
                "pir_human": payload["pir_human"],
                "chainsaw": payload["chainsaw_detected"],
                "thermal_human": payload["thermal_human"],
            },
        }
        self.latest_by_slot[slot] = packet
        self.last_emit_by_slot[slot] = now
        self.history.appendleft(packet)
        return packet

    def status(self) -> Dict[str, Any]:
        latest = [self.latest_by_slot[k] for k in sorted(self.latest_by_slot)]
        avg_pdr = None
        if latest:
            avg_pdr = round(sum(float(p.get("pdr_estimate_pct", 0)) for p in latest) / len(latest), 1)
        return {
            "enabled": bool(self.get_config().get("lora_enabled", True)),
            "simulation": True,
            "frequency_mhz": float(self.get_config().get("lora_frequency_mhz", 433.0)),
            "packet_count": len(self.history),
            "active_nodes": len(latest),
            "average_pdr_estimate_pct": avg_pdr,
            "latest": latest,
            "history": list(self.history),
        }
