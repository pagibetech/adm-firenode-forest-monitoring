#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]

import sys

sys.path.insert(0, str(APP_DIR))

from modules.lora_packet_store import LoraPacketStore
from modules.lora_simulator import LoraPacketSimulator
from modules.event_recorder import EventRecorder


def load_gateway_module():
    path = APP_DIR / "lora_gateway_serial.py"
    spec = importlib.util.spec_from_file_location("lora_gateway_serial", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LoraPipelineTests(unittest.TestCase):
    def test_gateway_status_line_is_ignored(self):
        gateway = load_gateway_module()
        self.assertEqual(gateway.parse_gateway_line('{"gateway_status":"ready","frequency_mhz":433.0}'), {})

    def test_gateway_packet_line_is_accepted(self):
        gateway = load_gateway_module()
        packet = gateway.parse_gateway_line(
            '{"packet_id":"GW-REMOTE-01-7","node_id":"REMOTE-01","seq":7,'
            '"rssi_dbm":-82,"snr_db":7.5,"payload":{"temperature_c":33.2}}'
        )
        self.assertEqual(packet["node_id"], "REMOTE-01")
        self.assertEqual(packet["seq"], 7)
        self.assertTrue(packet["received"])
        self.assertIn("timestamp", packet)

    def test_packet_store_deduplicates_packet_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = LoraPacketStore(str(Path(tmp) / "lora.db"))
            packet = {
                "packet_id": "SIM-LORA-1-1",
                "timestamp": "2026-05-13 22:00:00",
                "node_id": "REMOTE-01",
                "node_name": "Remote 01",
                "slot": 1,
                "seq": 1,
                "rssi_dbm": -75.0,
                "snr_db": 8.2,
                "pdr_estimate_pct": 96.0,
                "frequency_mhz": 433.0,
                "payload": {"temperature_c": 31.5, "battery_v": 12.3},
            }
            self.assertTrue(store.record(dict(packet)))
            self.assertFalse(store.record(dict(packet)))
            rows = store.recent(10)
            self.assertEqual(store.count(), 1)
            self.assertEqual(rows[0]["payload"]["battery_v"], 12.3)

    def test_simulator_packet_has_receiver_metrics(self):
        cfg = {
            "lora_frequency_mhz": 433.0,
            "lora_spreading_factor": 7,
            "lora_bandwidth_khz": 125.0,
            "lora_sim_interval_sec": 1,
        }
        sim = LoraPacketSimulator(lambda: cfg)
        packet = sim.packet_for_node(
            2,
            "Remote-Node-2-SIM",
            {"temperature": 30.1, "humidity": 66.5, "smoke": 180, "smoke_detected": False},
            {"confirmed_detection": False, "score": 14},
            {"detection": {"human_detected": False, "max_temp_c": 29.4}},
        )
        self.assertEqual(packet["slot"], 2)
        self.assertEqual(packet["seq"], 1)
        self.assertIn("rssi_dbm", packet)
        self.assertIn("snr_db", packet)
        self.assertIn("battery_v", packet["payload"])

    def test_event_recorder_writes_metadata_and_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = EventRecorder(tmp, lambda: {"event_recording_enabled": True})
            result = recorder.record_snapshot_event(
                "FireNode-Test",
                "CHAINSAW",
                {"score": 88},
                frame_jpeg=b"\xff\xd8\xff\xd9",
            )
            self.assertTrue(result["ok"])
            self.assertTrue(Path(result["metadata_path"]).exists())
            self.assertTrue((Path(result["event_dir"]) / "camera0.jpg").exists())
            self.assertEqual(len(recorder.recent(10)), 1)


if __name__ == "__main__":
    unittest.main()
