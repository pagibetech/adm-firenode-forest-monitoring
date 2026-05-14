#!/usr/bin/env python3
from __future__ import annotations

import io
import math
import threading
import time
from collections import deque
from typing import Any, Dict, Optional, Tuple

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = ImageDraw = ImageFont = None

THERMAL_PALETTE = None
if np is not None:
    THERMAL_PALETTE = np.array([
        [0, 0, 0],
        [0, 0, 120],
        [0, 110, 255],
        [0, 220, 180],
        [255, 180, 0],
        [255, 70, 0],
        [180, 0, 0],
        [255, 255, 255],
    ], dtype=np.float32)


def _cfg(cfg: Dict[str, Any], key: str, default: Any) -> Any:
    # Main app uses thermal_* keys. Also accept original MLX test keys for easier future merging.
    if "thermal_" + key in cfg:
        return cfg.get("thermal_" + key, default)
    return cfg.get(key, default)


def parse_address(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value).strip().lower()
    if text.startswith("0x"):
        return int(text, 16)
    return int(text)


def apply_orientation(frame, cfg: Dict[str, Any]):
    arr = frame
    rotate = int(_cfg(cfg, "rotate_degrees", 0)) % 360
    if rotate == 90:
        arr = np.rot90(arr, k=1)
    elif rotate == 180:
        arr = np.rot90(arr, k=2)
    elif rotate == 270:
        arr = np.rot90(arr, k=3)
    if bool(_cfg(cfg, "mirror_x", False)):
        arr = np.fliplr(arr)
    if bool(_cfg(cfg, "mirror_y", False)):
        arr = np.flipud(arr)
    return arr


def connected_components(mask) -> Tuple[int, Optional[Tuple[int, int, int, int]]]:
    h, w = mask.shape
    visited = np.zeros_like(mask, dtype=bool)
    largest_area = 0
    largest_bbox = None
    for y in range(h):
        for x in range(w):
            if not mask[y, x] or visited[y, x]:
                continue
            q = deque([(x, y)])
            visited[y, x] = True
            area = 0
            min_x = max_x = x
            min_y = max_y = y
            while q:
                cx, cy = q.popleft()
                area += 1
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for ny in range(max(0, cy - 1), min(h, cy + 2)):
                    for nx in range(max(0, cx - 1), min(w, cx + 2)):
                        if visited[ny, nx] or not mask[ny, nx]:
                            continue
                        visited[ny, nx] = True
                        q.append((nx, ny))
            if area > largest_area:
                largest_area = area
                largest_bbox = (min_x, min_y, max_x, max_y)
    return largest_area, largest_bbox


def detect_human(frame, cfg: Dict[str, Any]) -> Dict[str, Any]:
    if np is None or frame is None:
        return {
            "human_detected": False,
            "reason": "thermal library/frame unavailable",
            "ambient_c": None,
            "max_temp_c": None,
            "min_temp_c": None,
            "avg_temp_c": None,
            "largest_blob_pixels": 0,
            "bbox": None,
            "score": 0,
        }

    min_human = float(_cfg(cfg, "min_human_temp_c", 28.0))
    max_human = float(_cfg(cfg, "max_human_temp_c", 42.0))
    min_delta = float(_cfg(cfg, "min_delta_above_ambient_c", 4.0))
    min_blob = int(_cfg(cfg, "min_blob_pixels", 5))

    clean = np.nan_to_num(frame, nan=0.0, posinf=0.0, neginf=0.0)
    min_temp = float(np.min(clean))
    max_temp = float(np.max(clean))
    avg_temp = float(np.mean(clean))
    ambient = float(np.percentile(clean, 40))

    in_temp_range = (clean >= min_human) & (clean <= max_human)
    hotter_than_ambient = (clean - ambient) >= min_delta
    mask = in_temp_range & hotter_than_ambient
    largest_blob, bbox = connected_components(mask)
    detected = bool(largest_blob >= min_blob)

    blob_score = min(1.0, largest_blob / max(1, min_blob * 3))
    heat_score = min(1.0, max(0.0, (max_temp - min_human) / max(1.0, min_delta + 6.0)))
    score = int(round(100 * (0.60 * blob_score + 0.40 * heat_score)))

    if detected:
        reason = "thermal blob matched thresholds"
    elif max_temp < min_human:
        reason = "max temperature below human minimum"
    elif largest_blob < min_blob:
        reason = "thermal blob too small"
    else:
        reason = "thresholds not met"

    return {
        "human_detected": detected,
        "reason": reason,
        "ambient_c": round(ambient, 2),
        "max_temp_c": round(max_temp, 2),
        "min_temp_c": round(min_temp, 2),
        "avg_temp_c": round(avg_temp, 2),
        "largest_blob_pixels": int(largest_blob),
        "bbox": list(bbox) if bbox else None,
        "score": score,
    }


def palette_image(frame, cfg: Dict[str, Any]):
    display_min = float(_cfg(cfg, "display_min_c", 20.0))
    display_max = float(_cfg(cfg, "display_max_c", 45.0))
    if display_max <= display_min:
        display_max = display_min + 1.0
    norm = np.clip((frame - display_min) / (display_max - display_min), 0, 1)
    scaled = norm * (len(THERMAL_PALETTE) - 1)
    idx0 = np.floor(scaled).astype(np.int32)
    idx1 = np.clip(idx0 + 1, 0, len(THERMAL_PALETTE) - 1)
    frac = (scaled - idx0)[..., None]
    rgb = THERMAL_PALETTE[idx0] * (1 - frac) + THERMAL_PALETTE[idx1] * frac
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    return Image.fromarray(rgb, mode="RGB")


def make_overlay_png(frame, detection: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[bytes]:
    if np is None or Image is None:
        return None
    if frame is None:
        frame = np.zeros((24, 32), dtype=np.float32)
    img = palette_image(frame, cfg)
    out_w = 640
    out_h = int(round(out_w * frame.shape[0] / frame.shape[1]))
    img = img.resize((out_w, out_h), resample=Image.Resampling.BICUBIC)
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 18)
        big_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
    except Exception:
        font = ImageFont.load_default()
        big_font = font

    detected = bool(detection.get("human_detected", False))
    status_text = "THERMAL HUMAN DETECTED" if detected else "NO THERMAL HUMAN DETECTED"
    max_temp = detection.get("max_temp_c")
    ambient = detection.get("ambient_c")
    score = detection.get("score", 0)
    draw.rectangle([(0, 0), (out_w, 64)], fill=(0, 0, 0))
    draw.text((10, 8), status_text, fill=(255, 255, 255), font=big_font)
    draw.text((10, 38), f"Max: {max_temp} C | Ambient: {ambient} C | Score: {score}%", fill=(255, 255, 255), font=font)

    bbox = detection.get("bbox")
    if detected and bbox:
        x1, y1, x2, y2 = bbox
        sx = out_w / frame.shape[1]
        sy = out_h / frame.shape[0]
        rect = (int(x1 * sx), int(y1 * sy), int((x2 + 1) * sx), int((y2 + 1) * sy))
        for t in range(4):
            draw.rectangle([(rect[0] - t, rect[1] - t), (rect[2] + t, rect[3] + t)], outline=(255, 255, 255))

    bar_x1, bar_y1 = out_w - 42, 80
    bar_x2, bar_y2 = out_w - 22, out_h - 20
    bar_h = max(1, bar_y2 - bar_y1)
    display_min = float(_cfg(cfg, "display_min_c", 20.0))
    display_max = float(_cfg(cfg, "display_max_c", 45.0))
    for i in range(bar_h):
        n = 1.0 - (i / max(1, bar_h - 1))
        one = np.array([[display_min + n * (display_max - display_min)]], dtype=np.float32)
        color = palette_image(one, cfg).getpixel((0, 0))
        draw.line([(bar_x1, bar_y1 + i), (bar_x2, bar_y1 + i)], fill=color)
    draw.rectangle([(bar_x1, bar_y1), (bar_x2, bar_y2)], outline=(255, 255, 255))
    draw.text((out_w - 100, bar_y1 - 4), f"{display_max:g}C", fill=(255, 255, 255), font=font)
    draw.text((out_w - 100, bar_y2 - 18), f"{display_min:g}C", fill=(255, 255, 255), font=font)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class ThermalCameraService:
    def __init__(self, get_config):
        self.get_config = get_config
        self.lock = threading.Lock()
        self.frame = None
        self.png: Optional[bytes] = None
        self.detection = detect_human(None, {})
        self.last_frame_time = 0.0
        self.frame_count = 0
        self.fps = 0.0
        self.error: Optional[str] = None
        self.sensor = None
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.running = False
        self.simulation = False
        self._sim_phase = 0.0

    def start(self) -> bool:
        cfg = self.get_config()
        if not bool(cfg.get("thermal_enabled", False)):
            self.stop()
            return False
        if np is None or Image is None:
            with self.lock:
                self.error = "numpy or pillow is not installed"
                self.running = False
            return False
        with self.lock:
            if self.thread and self.thread.is_alive():
                return False
            self.stop_event.clear()
            self.running = True
            self.simulation = bool(cfg.get("thermal_simulation", False))
        if not self.simulation:
            self._init_sensor(cfg)
        self.thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self) -> bool:
        with self.lock:
            thread = self.thread
            if not thread or not thread.is_alive():
                self.running = False
                return False
            self.stop_event.set()
        thread.join(timeout=2.0)
        with self.lock:
            self.running = False
            self.thread = None
        return True

    def restart(self) -> bool:
        self.stop()
        return self.start()

    def _init_sensor(self, cfg: Dict[str, Any]) -> None:
        try:
            import board
            import busio
            import adafruit_mlx90640
            try:
                i2c = busio.I2C(board.SCL, board.SDA, frequency=400000)
            except TypeError:
                i2c = busio.I2C(board.SCL, board.SDA)
            address = parse_address(cfg.get("thermal_i2c_address", "0x33"))
            mlx = adafruit_mlx90640.MLX90640(i2c, address=address)
            rate = int(float(cfg.get("thermal_refresh_rate_hz", 2)))
            rate_map = {
                1: adafruit_mlx90640.RefreshRate.REFRESH_1_HZ,
                2: adafruit_mlx90640.RefreshRate.REFRESH_2_HZ,
                4: adafruit_mlx90640.RefreshRate.REFRESH_4_HZ,
                8: adafruit_mlx90640.RefreshRate.REFRESH_8_HZ,
            }
            mlx.refresh_rate = rate_map.get(rate, adafruit_mlx90640.RefreshRate.REFRESH_2_HZ)
            with self.lock:
                self.sensor = mlx
                self.error = None
                self.simulation = False
        except Exception as exc:
            with self.lock:
                self.sensor = None
                self.error = f"MLX90640 init failed, using simulation: {exc}"
                self.simulation = True

    def _simulate_frame(self):
        h, w = 24, 32
        ambient = 25.0 + math.sin(self._sim_phase / 20.0) * 1.5
        frame = np.random.normal(loc=ambient, scale=0.35, size=(h, w)).astype(np.float32)
        cx = 16 + 8 * math.sin(self._sim_phase / 15.0)
        cy = 12 + 5 * math.cos(self._sim_phase / 22.0)
        blob_temp = 34.0 + 1.8 * math.sin(self._sim_phase / 8.0)
        yy, xx = np.mgrid[0:h, 0:w]
        blob = np.exp(-(((xx - cx) ** 2) / (2 * 3.0 ** 2) + ((yy - cy) ** 2) / (2 * 4.0 ** 2)))
        frame += blob * (blob_temp - ambient)
        if int(self._sim_phase) % 40 > 30:
            frame[4:6, 25:27] = 38.0
        self._sim_phase += 1.0
        return frame

    def _reader_loop(self) -> None:
        last_fps_time = time.time()
        frames_since = 0
        raw = [0.0] * 768
        while not self.stop_event.is_set():
            try:
                cfg = self.get_config()
                with self.lock:
                    sim = self.simulation or self.sensor is None
                    sensor = self.sensor
                if sim:
                    arr = self._simulate_frame()
                    time.sleep(0.25)
                else:
                    try:
                        sensor.getFrame(raw)
                    except ValueError:
                        time.sleep(0.02)
                        continue
                    arr = np.array(raw, dtype=np.float32).reshape((24, 32))
                oriented = apply_orientation(arr, cfg)
                detection = detect_human(oriented, cfg)
                png = make_overlay_png(oriented, detection, cfg)
                now = time.time()
                with self.lock:
                    self.frame = oriented
                    self.detection = detection
                    self.png = png
                    self.last_frame_time = now
                    self.frame_count += 1
                    self.running = True
                    if self.error and not self.simulation:
                        self.error = None
                frames_since += 1
                if now - last_fps_time >= 2.0:
                    with self.lock:
                        self.fps = round(frames_since / (now - last_fps_time), 2)
                    frames_since = 0
                    last_fps_time = now
            except Exception as exc:
                with self.lock:
                    self.error = str(exc)
                time.sleep(0.5)
        with self.lock:
            self.running = False

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "enabled": bool(self.get_config().get("thermal_enabled", False)),
                "running": bool(self.running),
                "simulation": bool(self.simulation),
                "fps": self.fps,
                "frame_count": self.frame_count,
                "last_frame_time": self.last_frame_time,
                "error": self.error,
                "detection": dict(self.detection),
            }

    def get_png(self) -> Optional[bytes]:
        with self.lock:
            return self.png

    def placeholder_png(self, text: str = "Thermal unavailable") -> Optional[bytes]:
        if Image is None:
            return None
        img = Image.new("RGB", (640, 480), color=(0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        except Exception:
            font = ImageFont.load_default()
        draw.text((30, 210), text, fill=(255, 255, 255), font=font)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def mjpeg_generator(self):
        while True:
            if not bool(self.get_config().get("thermal_enabled", False)):
                frame = self.placeholder_png("Thermal disabled")
            else:
                if not self.get_status().get("running"):
                    self.start()
                frame = self.get_png() or self.placeholder_png("Waiting for MLX90640")
            if frame:
                yield (b"--frame\r\n"
                       b"Content-Type: image/png\r\n"
                       b"Cache-Control: no-cache\r\n\r\n" + frame + b"\r\n")
            time.sleep(0.20)
