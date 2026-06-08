#!/usr/bin/env python3
from __future__ import annotations

import io
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    from picamera2 import Picamera2
except Exception:  # pragma: no cover
    Picamera2 = None

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None


class CsiCameraStream:
    """Raspberry Pi CSI camera stream using Picamera2. Outputs JPEG frames for Flask MJPEG."""

    def __init__(self, get_config: Callable[[], Dict[str, Any]]):
        self.get_config = get_config
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.frame_jpeg: Optional[bytes] = None
        self.status: Dict[str, Any] = {
            "running": False,
            "available": Picamera2 is not None,
            "error": None,
            "frames": 0,
            "device_index": "csi",
        }
        self._picam2: Optional[Any] = None

    def start(self) -> bool:
        if Picamera2 is None:
            with self.lock:
                self.status.update({
                    "running": False,
                    "available": False,
                    "error": "picamera2 is not installed",
                })
            return False
        with self.lock:
            if self.thread and self.thread.is_alive():
                return False
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.status.update({"running": True, "error": None})
            self.thread.start()
            return True

    def stop(self) -> bool:
        with self.lock:
            thread = self.thread
            if not thread or not thread.is_alive():
                self.status["running"] = False
                return False
            self.stop_event.set()
        thread.join(timeout=3.0)
        with self.lock:
            self.status["running"] = False
        self._close_camera()
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return dict(self.status)

    def get_frame(self) -> Optional[bytes]:
        with self.lock:
            return self.frame_jpeg

    def _load_font(self, size: int, bold: bool = False):
        if ImageFont is None:
            return None
        try:
            name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            return ImageFont.truetype(name, size)
        except Exception:
            return ImageFont.load_default()

    def _placeholder(self, text: str = "CSI Camera unavailable") -> Optional[bytes]:
        cfg = self.get_config()
        width = max(320, min(int(cfg.get("camera_width", 640) or 640), 1920))
        height = max(240, min(int(cfg.get("camera_height", 480) or 480), 1080))
        quality = max(30, min(95, int(cfg.get("camera_jpeg_quality", 85) or 85)))

        if Image is None or ImageDraw is None:
            return None

        img = Image.new("RGB", (width, height), (12, 20, 32))
        draw = ImageDraw.Draw(img)
        title_font = self._load_font(28, True)
        body_font = self._load_font(17, False)

        draw.rectangle([(0, 0), (width, 72)], fill=(0, 0, 0))
        draw.text((18, 12), "Raspberry Pi CSI Camera", fill=(255, 255, 255), font=title_font)
        draw.text((18, 46), time.strftime("%Y-%m-%d %H:%M:%S"), fill=(188, 210, 235), font=body_font)
        draw.rectangle([(20, 98), (width - 20, height - 58)], outline=(95, 155, 220), width=3)
        draw.text((34, height // 2 - 12), text[:72], fill=(235, 242, 250), font=body_font)
        draw.text((18, height - 36), "Picamera2 CSI fallback placeholder", fill=(194, 208, 225), font=body_font)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    def _close_camera(self) -> None:
        if self._picam2 is not None:
            try:
                self._picam2.stop()
                self._picam2.close()
            except Exception:
                pass
            self._picam2 = None

    def _open_camera(self, cfg: Dict[str, Any]):
        width = max(320, min(int(cfg.get("camera_width", 640) or 640), 2592))
        height = max(240, min(int(cfg.get("camera_height", 480) or 480), 1944))
        fps = max(1, int(cfg.get("camera_fps", 15) or 15))

        picam2 = Picamera2()
        camera_config = picam2.create_still_configuration(
            main={"size": (width, height), "format": "RGB888"}
        )
        picam2.configure(camera_config)
        picam2.start()
        return picam2, width, height, fps

    def _loop(self) -> None:
        try:
            cfg = self.get_config()
            self._picam2, width, height, fps = self._open_camera(cfg)
            quality = max(30, min(95, int(cfg.get("camera_jpeg_quality", 85) or 85)))
            sleep_interval = 1.0 / fps

            with self.lock:
                self.status.update({
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "jpeg_quality": quality,
                    "running": True,
                    "available": True,
                    "error": None,
                })

            while not self.stop_event.is_set():
                try:
                    buffer = io.BytesIO()
                    self._picam2.capture_file(buffer, format="jpeg")
                    jpeg_bytes = buffer.getvalue()
                except Exception as e:
                    with self.lock:
                        self.status["error"] = f"capture_file failed: {e}"
                    time.sleep(0.5)
                    continue

                if jpeg_bytes:
                    with self.lock:
                        self.frame_jpeg = jpeg_bytes
                        self.status["frames"] = int(self.status.get("frames", 0)) + 1
                        self.status["error"] = None
                time.sleep(sleep_interval)

        except Exception as e:
            with self.lock:
                self.status.update({"running": False, "error": str(e)})
        finally:
            self._close_camera()
            with self.lock:
                self.status["running"] = False

    def mjpeg_generator(self):
        while True:
            frame = self.get_frame()
            if frame is None:
                frame = self._placeholder("Waiting for CSI camera")
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n"
                       b"Cache-Control: no-cache\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.08)
