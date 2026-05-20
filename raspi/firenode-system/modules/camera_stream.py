#!/usr/bin/env python3
from __future__ import annotations

import io
import math
import os
import platform
import threading
import time
from typing import Any, Callable, Dict, Optional

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None
    ImageFont = None


class CameraStream:
    def __init__(self, get_config: Callable[[], Dict[str, Any]]):
        self.get_config = get_config
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.frame_jpeg: Optional[bytes] = None
        self.status: Dict[str, Any] = {
            "running": False,
            "available": cv2 is not None,
            "error": None,
            "frames": 0,
            "device_index": 0,
        }

    def start(self) -> bool:
        if cv2 is None:
            if self._simulation_enabled():
                with self.lock:
                    if self.thread and self.thread.is_alive():
                        return False
                    self.stop_event.clear()
                    self.thread = threading.Thread(target=self._simulation_loop, daemon=True)
                    self.status.update({"running": True, "available": True, "error": None, "simulation": True})
                    self.thread.start()
                    return True
            with self.lock:
                self.status.update({"running": False, "available": False, "error": "python3-opencv/cv2 is not installed"})
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
        thread.join(timeout=2.0)
        with self.lock:
            self.status["running"] = False
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

    def _simulation_enabled(self) -> bool:
        try:
            return str(self.get_config().get("operation_mode", "live")).lower() == "simulation"
        except Exception:
            return False

    def _load_font(self, size: int, bold: bool = False):
        if ImageFont is None:
            return None
        try:
            name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
            return ImageFont.truetype(name, size)
        except Exception:
            return ImageFont.load_default()

    def _placeholder(self, text: str = "Camera unavailable") -> Optional[bytes]:
        cfg = self.get_config()
        width = max(320, min(int(cfg.get("camera_width", 640) or 640), 1280))
        height = max(240, min(int(cfg.get("camera_height", 480) or 480), 720))
        quality = max(30, min(95, int(cfg.get("camera_jpeg_quality", 70) or 70)))
        device_index = int(cfg.get("camera_device_index", 0))

        if cv2 is None or np is None:
            if Image is None or ImageDraw is None:
                return None
            img = Image.new("RGB", (width, height), (12, 20, 32))
            draw = ImageDraw.Draw(img)
            title_font = self._load_font(28, True)
            body_font = self._load_font(17, False)
            draw.rectangle([(0, 0), (width, 72)], fill=(0, 0, 0))
            draw.text((18, 12), f"LOCAL CAMERA /dev/video{device_index}", fill=(255, 255, 255), font=title_font)
            draw.text((18, 46), time.strftime("%Y-%m-%d %H:%M:%S"), fill=(188, 210, 235), font=body_font)
            draw.rectangle([(20, 98), (width - 20, height - 58)], outline=(95, 155, 220), width=3)
            draw.text((34, height // 2 - 12), text[:72], fill=(235, 242, 250), font=body_font)
            draw.text((18, height - 36), "Simulation fallback: install python3-opencv on Raspberry Pi for live USB camera.", fill=(194, 208, 225), font=body_font)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            return buf.getvalue()

        img = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(img, text[:38], (18, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 2)
        ok, enc = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        return enc.tobytes() if ok else None

    def _simulation_frame(self) -> Optional[bytes]:
        if Image is None or ImageDraw is None:
            return self._placeholder("Pillow/PIL is not installed")
        cfg = self.get_config()
        width = max(320, min(int(cfg.get("camera_width", 640) or 640), 1280))
        height = max(240, min(int(cfg.get("camera_height", 480) or 480), 720))
        quality = max(30, min(95, int(cfg.get("camera_jpeg_quality", 70) or 70)))
        device_index = int(cfg.get("camera_device_index", 0))
        t = time.time()

        img = Image.new("RGB", (width, height), (9, 18, 32))
        draw = ImageDraw.Draw(img)
        title_font = self._load_font(28, True)
        body_font = self._load_font(17, False)
        small_font = self._load_font(14, False)

        offset = int((t * 22 + device_index * 17) % 90)
        for x in range(-90 + offset, width, 90):
            draw.line([(x, 0), (x + 130, height)], fill=(18, 43, 72), width=2)
        for y in range(0, height, 64):
            draw.line([(0, y), (width, y)], fill=(18, 34, 58), width=1)

        cx = int(width * (0.28 + 0.44 * ((math.sin(t / 2.8 + device_index) + 1) / 2)))
        cy = int(height * (0.48 + 0.16 * math.sin(t / 2.0 + device_index)))
        draw.rectangle([(cx - 70, cy - 86), (cx + 70, cy + 86)], outline=(255, 255, 255), width=2)
        draw.ellipse([(cx - 38, cy - 68), (cx + 38, cy + 68)], outline=(71, 166, 255), width=4)

        draw.rectangle([(0, 0), (width, 74)], fill=(0, 0, 0))
        draw.text((18, 10), f"MAIN NODE CAMERA /dev/video{device_index}", fill=(255, 255, 255), font=title_font)
        draw.text((18, 45), time.strftime("%Y-%m-%d %H:%M:%S"), fill=(188, 210, 235), font=body_font)
        badge = "SIMULATION"
        draw.rounded_rectangle([(width - 154, 17), (width - 18, 56)], radius=10, fill=(32, 118, 92))
        draw.text((width - 138, 27), badge, fill=(255, 255, 255), font=small_font)
        draw.text((18, height - 34), "Local daytime camera fallback for dashboard testing without OpenCV or USB camera hardware.", fill=(210, 222, 238), font=small_font)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return buf.getvalue()

    def _simulation_loop(self) -> None:
        try:
            while not self.stop_event.is_set():
                cfg = self.get_config()
                fps = max(1, int(cfg.get("camera_fps", 10) or 10))
                frame = self._simulation_frame()
                with self.lock:
                    if frame:
                        self.frame_jpeg = frame
                    self.status.update({
                        "running": True,
                        "available": True,
                        "simulation": True,
                        "error": None,
                        "frames": int(self.status.get("frames", 0)) + 1,
                        "device_index": int(cfg.get("camera_device_index", 0)),
                        "width": int(cfg.get("camera_width", 640) or 640),
                        "height": int(cfg.get("camera_height", 480) or 480),
                        "fps": fps,
                    })
                time.sleep(1.0 / fps)
        except Exception as e:
            with self.lock:
                self.status.update({"running": False, "error": str(e)})
        finally:
            with self.lock:
                self.status["running"] = False

    def _camera_device(self, device_index: int) -> Any:
        path = f"/dev/video{device_index}"
        if os.name == "posix" and os.path.exists(path):
            return path
        return device_index

    def _backend_flag(self, backend_name: str) -> Optional[int]:
        if cv2 is None:
            return None
        backend = str(backend_name or "V4L2").strip().upper()
        if backend in ("", "AUTO", "DEFAULT", "ANY"):
            return None
        if backend == "V4L2" and platform.system().lower() == "linux" and hasattr(cv2, "CAP_V4L2"):
            return int(cv2.CAP_V4L2)
        attr = f"CAP_{backend}"
        if hasattr(cv2, attr):
            try:
                return int(getattr(cv2, attr))
            except Exception:
                return None
        return None

    def _open_capture(self, cfg: Dict[str, Any]):
        device_index = int(cfg.get("camera_device_index", 0))
        backend_name = str(cfg.get("camera_backend", "V4L2") or "V4L2").strip().upper()
        fourcc = str(cfg.get("camera_fourcc", "MJPG") or "MJPG").strip().upper()[:4] or "MJPG"
        width = int(cfg.get("camera_width", 640) or 640)
        height = int(cfg.get("camera_height", 480) or 480)
        fps = max(1, int(cfg.get("camera_fps", 10) or 10))
        warmup_frames = max(0, int(cfg.get("camera_open_warmup_frames", 5) or 0))
        device = self._camera_device(device_index)
        backend = self._backend_flag(backend_name)

        if backend is not None:
            cap = cv2.VideoCapture(device, backend)
        else:
            cap = cv2.VideoCapture(device)

        if cap is not None and cap.isOpened():
            try:
                if fourcc and len(fourcc) == 4:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                cap.set(cv2.CAP_PROP_FPS, fps)
            except Exception:
                pass
            for _ in range(warmup_frames):
                if self.stop_event.is_set():
                    break
                try:
                    cap.read()
                except Exception:
                    break

        with self.lock:
            self.status.update({
                "device_index": device_index,
                "device": str(device),
                "backend": backend_name if backend is not None else "AUTO",
                "fourcc": fourcc,
                "width": width,
                "height": height,
                "fps": fps,
                "warmup_frames": warmup_frames,
            })
        return cap

    def _loop(self) -> None:
        cap = None
        try:
            while not self.stop_event.is_set():
                cfg = self.get_config()
                device_index = int(cfg.get("camera_device_index", 0))
                width = int(cfg.get("camera_width", 640))
                height = int(cfg.get("camera_height", 480))
                fps = max(1, int(cfg.get("camera_fps", 10)))
                quality = max(30, min(95, int(cfg.get("camera_jpeg_quality", 70))))
                retry_on_failed_read = bool(cfg.get("camera_retry_on_failed_read", True))

                if cap is None or not cap.isOpened():
                    cap = self._open_capture(cfg)

                if cap is None or not cap.isOpened():
                    with self.lock:
                        self.status.update({"running": True, "error": f"Cannot open /dev/video{device_index}"})
                        self.frame_jpeg = self._placeholder(f"No camera /dev/video{device_index}")
                    time.sleep(2.0)
                    continue

                ok, frame = cap.read()
                if not ok or frame is None:
                    with self.lock:
                        self.status["error"] = "Camera frame read failed; reopening" if retry_on_failed_read else "Camera frame read failed"
                    if retry_on_failed_read:
                        try:
                            cap.release()
                        except Exception:
                            pass
                        cap = None
                    time.sleep(0.5)
                    continue

                ok, enc = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
                if ok:
                    with self.lock:
                        self.frame_jpeg = enc.tobytes()
                        self.status["frames"] = int(self.status.get("frames", 0)) + 1
                        self.status["running"] = True
                        self.status["available"] = True
                        self.status["error"] = None

                time.sleep(1.0 / fps)
        except Exception as e:
            with self.lock:
                self.status.update({"running": False, "error": str(e)})
        finally:
            try:
                if cap is not None:
                    cap.release()
            except Exception:
                pass
            with self.lock:
                self.status["running"] = False

    def mjpeg_generator(self):
        while True:
            frame = self.get_frame()
            if frame is None:
                frame = self._placeholder("Waiting for camera")
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n"
                       b"Cache-Control: no-cache\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.08)
