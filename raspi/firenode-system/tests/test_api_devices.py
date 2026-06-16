#!/usr/bin/env python3
"""Tests for /api/devices audio device enumeration with arecord fallback logic."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from app import app as flask_app


class ApiDevicesTests(unittest.TestCase):
    """Test /api/devices enumeration logic, especially arecord no-hardware cases."""

    def setUp(self):
        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

    @staticmethod
    def _make_proc(returncode, stdout, stderr=""):
        """Create a CompletedProcess-like object."""
        proc = MagicMock(spec=subprocess.CompletedProcess)
        proc.returncode = returncode
        proc.stdout = stdout
        proc.stderr = stderr
        return proc

    def test_arecord_success_with_usb_mic_falls_through_to_sounddevice(self):
        """When arecord finds a USB mic, it cross-references with sounddevice."""
        proc = self._make_proc(
            0,
            "card 2: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]\n",
        )
        mock_devices = [
            {"name": "USB PnP Sound Device", "max_input_channels": 1, "default_samplerate": 44100.0},
            {"name": "dummy output", "max_input_channels": 0, "default_samplerate": 48000.0},
        ]
        with patch("subprocess.run", return_value=proc):
            with patch("sounddevice.query_devices", return_value=mock_devices):
                resp = self.client.get("/api/devices")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["devices"]), 1)
        self.assertEqual(data["devices"][0]["name"], "USB PnP Sound Device")

    def test_arecord_zero_with_empty_output_returns_empty(self):
        """When arecord returns 0 but no capture lines, return empty list."""
        proc = self._make_proc(0, "\n")
        with patch("subprocess.run", return_value=proc):
            # sounddevice must NOT be called — we patch it to fail if invoked
            with patch("sounddevice.query_devices", side_effect=RuntimeError("should not be called")):
                resp = self.client.get("/api/devices")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["devices"]), 0)
        self.assertEqual(data["meta"]["enumeration_source"], "alsa")
        self.assertEqual(data["meta"]["alsa_status"], "no_capture_lines")

    def test_arecord_nonzero_no_soundcards_returns_empty(self):
        """When arecord exits 1 with 'no soundcards found', return empty list."""
        proc = self._make_proc(1, "", "no soundcards found\n")
        with patch("subprocess.run", return_value=proc):
            with patch("sounddevice.query_devices", side_effect=RuntimeError("should not be called")):
                resp = self.client.get("/api/devices")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["devices"]), 0)
        self.assertEqual(data["meta"]["alsa_status"], "no_capture_devices")

    def test_arecord_nonzero_stale_portaudio_blocked(self):
        """When arecord says no devices, sounddevice stale cache must NOT leak through."""
        proc = self._make_proc(1, "", "no soundcard\n")
        stale_devices = [
            {"name": "USB PnP Sound Device", "max_input_channels": 1, "default_samplerate": 44100.0},
        ]
        with patch("subprocess.run", return_value=proc):
            with patch("sounddevice.query_devices", return_value=stale_devices):
                resp = self.client.get("/api/devices")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["devices"]), 0,
                         "stale PortAudio devices must not appear when arecord reports no hardware")

    def test_arecord_exit0_no_audio_devices_found_stderr(self):
        """arecord exit 0 with 'no audio devices found' in stderr returns empty (exit0 edge case)."""
        proc = self._make_proc(0, "", "no audio devices found\n")
        with patch("subprocess.run", return_value=proc):
            with patch("sounddevice.query_devices", side_effect=RuntimeError("should not be called")):
                resp = self.client.get("/api/devices")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["devices"]), 0)
        self.assertEqual(data["meta"]["alsa_status"], "no_capture_devices")
        self.assertEqual(data["meta"]["arecord_returncode"], 0)

    def test_arecord_exit1_cannot_access_returns_empty(self):
        """arecord exit 1 with 'cannot access' returns empty and blocks stale fallback."""
        proc = self._make_proc(1, "", "cannot access audio device\n")
        stale_devices = [{"name": "USB PnP Sound Device", "max_input_channels": 1, "default_samplerate": 44100.0}]
        with patch("subprocess.run", return_value=proc):
            with patch("sounddevice.query_devices", return_value=stale_devices):
                resp = self.client.get("/api/devices")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["devices"]), 0,
                         "stale PortAudio must be blocked when arecord reports no access")
        self.assertEqual(data["meta"]["arecord_returncode"], 1)

    def test_arecord_meta_includes_diagnostic_fields(self):
        """All response variants include arecord_returncode and enumeration_source in meta."""
        proc = self._make_proc(0, "card 0: Foo [Some Device], device 0: USB Audio [USB Audio]\n")
        mock_devices = [{"name": "Some Device", "max_input_channels": 1, "default_samplerate": 48000.0}]
        with patch("subprocess.run", return_value=proc):
            with patch("sounddevice.query_devices", return_value=mock_devices):
                resp = self.client.get("/api/devices")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertIn("meta", data)
        self.assertIn("arecord_returncode", data["meta"])
        self.assertIn("enumeration_source", data["meta"])

    def test_arecord_missing_falls_back_to_sounddevice(self):
        """When arecord is not installed, fall back to sounddevice."""
        mock_devices = [
            {"name": "Built-in Mic", "max_input_channels": 2, "default_samplerate": 48000.0},
        ]
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("sounddevice.query_devices", return_value=mock_devices):
                resp = self.client.get("/api/devices")
        data = json.loads(resp.data)
        self.assertTrue(data["ok"])
        self.assertEqual(len(data["devices"]), 1)
        self.assertEqual(data["devices"][0]["name"], "Built-in Mic")


if __name__ == "__main__":
    unittest.main()
