#!/usr/bin/env python3
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, List, Optional

from .camera_stream import CameraStream
from .csi_camera_stream import CsiCameraStream


def parse_camera_indexes(value: Any, fallback: int = 0) -> List[int]:
    """Accept list, comma/newline string, or single number and return unique camera indexes."""
    raw: List[Any]
    if isinstance(value, list):
        raw = value
    elif isinstance(value, tuple):
        raw = list(value)
    elif isinstance(value, str):
        text = value.replace(";", ",").replace("\n", ",")
        raw = [x.strip() for x in text.split(",") if x.strip() != ""]
    elif value is None:
        raw = [fallback]
    else:
        raw = [value]

    indexes: List[int] = []
    for item in raw:
        try:
            idx = int(item)
        except Exception:
            continue
        if idx < 0:
            continue
        if idx not in indexes:
            indexes.append(idx)
    if not indexes:
        indexes = [int(fallback)]
    return indexes


class MultiCameraManager:
    """Manages local cameras: CSI (Picamera2) primary, USB (OpenCV) fallback."""

    def __init__(self, get_config: Callable[[], Dict[str, Any]]):
        self.get_config = get_config
        self.lock = threading.Lock()
        self.streams: Dict[int, CameraStream] = {}
        self.csi_stream: Optional[CsiCameraStream] = None
        self._csi_active: bool = False

    def _csi_configured(self) -> bool:
        cfg = self.get_config()
        return str(cfg.get("camera_type", "csi")).lower() == "csi"

    def configured_indexes(self) -> List[int]:
        cfg = self.get_config()
        fallback = int(cfg.get("camera_device_index", 0))
        return parse_camera_indexes(cfg.get("camera_device_indexes", [fallback]), fallback=fallback)

    def _config_for_index(self, index: int) -> Callable[[], Dict[str, Any]]:
        def _getter() -> Dict[str, Any]:
            cfg = dict(self.get_config())
            cfg["camera_device_index"] = int(index)
            return cfg
        return _getter

    def _start_csi(self) -> bool:
        if self.csi_stream is None:
            self.csi_stream = CsiCameraStream(self.get_config)
        return self.csi_stream.start()

    def _stop_csi(self) -> None:
        if self.csi_stream is not None:
            self.csi_stream.stop()
            self.csi_stream = None
        self._csi_active = False

    def _sync_usb_streams(self, start_missing: bool = True) -> None:
        cfg = self.get_config()
        enabled = bool(cfg.get("camera_enabled", True))
        indexes = self.configured_indexes()
        with self.lock:
            for idx in list(self.streams.keys()):
                if idx not in indexes or not enabled:
                    self.streams[idx].stop()
                    self.streams.pop(idx, None)
            if not enabled:
                return
            for idx in indexes:
                if idx not in self.streams:
                    self.streams[idx] = CameraStream(self._config_for_index(idx))
                if start_missing:
                    self.streams[idx].start()

    def sync_streams(self, start_missing: bool = True) -> None:
        cfg = self.get_config()
        enabled = bool(cfg.get("camera_enabled", True))
        use_csi = self._csi_configured()

        if use_csi and enabled:
            # Stop any USB streams before attempting CSI
            with self.lock:
                for idx in list(self.streams.keys()):
                    self.streams[idx].stop()
                    self.streams.pop(idx, None)
            if start_missing:
                ok = self._start_csi()
                if ok:
                    self._csi_active = True
                    return
                # CSI failed; fall back to USB if allowed
                self._stop_csi()
                if bool(cfg.get("camera_usb_fallback", True)):
                    self._sync_usb_streams(start_missing=start_missing)
            return

        # USB mode or disabled
        self._stop_csi()
        self._sync_usb_streams(start_missing=start_missing)

    def start_all(self) -> None:
        self.sync_streams(start_missing=True)

    def stop_all(self) -> None:
        with self.lock:
            for stream in self.streams.values():
                stream.stop()
            self.streams.clear()
        self._stop_csi()

    def restart_all(self) -> None:
        self.stop_all()
        self.start_all()

    def get_stream(self, index: int) -> Any:
        if self._csi_active and self.csi_stream is not None:
            return self.csi_stream
        idx = int(index)
        with self.lock:
            if idx not in self.streams:
                self.streams[idx] = CameraStream(self._config_for_index(idx))
            stream = self.streams[idx]
        if bool(self.get_config().get("camera_enabled", True)) and not stream.get_status().get("running"):
            stream.start()
        return stream

    def get_status(self) -> Dict[str, Any]:
        self.sync_streams(start_missing=False)
        cfg = self.get_config()
        enabled = bool(cfg.get("camera_enabled", True))

        if self._csi_active and self.csi_stream is not None:
            csi_status = self.csi_stream.get_status()
            csi_status["device_index"] = 0
            csi_status["camera_type"] = "csi"
            return {
                "enabled": enabled,
                "primary": csi_status,
                "cameras": [csi_status],
                "camera_count": 1,
                "configured_indexes": [0],
                # Backward compatibility fields
                **csi_status,
            }

        # USB mode
        configured = self.configured_indexes()
        cameras = []
        with self.lock:
            for idx in configured:
                stream = self.streams.get(idx)
                status = stream.get_status() if stream else {
                    "running": False,
                    "available": True,
                    "error": "Not started",
                    "frames": 0,
                    "device_index": idx,
                    "camera_type": "usb",
                }
                status["device_index"] = idx
                status["camera_type"] = "usb"
                cameras.append(status)
        primary = cameras[0] if cameras else {"running": False, "device_index": configured[0] if configured else 0, "camera_type": "usb"}
        return {
            "enabled": enabled,
            "primary": primary,
            "cameras": cameras,
            "camera_count": len(cameras),
            "configured_indexes": configured,
            # Backward compatibility fields used by older UI code.
            **primary,
        }

    def mjpeg_generator(self, index: int):
        if self._csi_active and self.csi_stream is not None:
            return self.csi_stream.mjpeg_generator()
        return self.get_stream(int(index)).mjpeg_generator()
