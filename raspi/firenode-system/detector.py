#!/usr/bin/env python3
"""
Lightweight chainsaw-like sound detector for Raspberry Pi 3B.

This is a test/prototype detector. It does not use a trained ML model.
It detects loud rough mechanical sound patterns using:
- RMS loudness
- engine-band energy
- chain/high-frequency-band energy
- broadband mechanical energy ratio
- multi-window confirmation

Designed for forest use where motorcycle/generator false positives are not expected.

Version 2 update:
- Live USB microphone detection
- Audio-file detection using WAV directly or ffmpeg for MP3/M4A/AAC/FLAC/OGG
- File-analysis audio features are returned the same way live features are returned
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import subprocess
import threading
import time
import wave
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


SUPPORTED_AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg")

DEFAULT_CONFIG: Dict[str, Any] = {
    "sample_rate": 16000,
    "window_sec": 1.0,
    "score_threshold": 60,
    "min_rms": 0.015,
    "require_hits": 3,
    "history_windows": 5,
    "cooldown_sec": 30,
    "auto_start": True,
    "detection_mode": "live",  # live or file
    "input_device": None,
    "audio_browse_start_dir": "test_audio",
    "host": "0.0.0.0",
    "port": 8080,
    "log_file": "detections.csv",
}


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_config(path: str = "config.json") -> Dict[str, Any]:
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                cfg.update(loaded)
        except Exception:
            pass
    if cfg.get("detection_mode") not in ("live", "file"):
        cfg["detection_mode"] = "live"
    return cfg


def save_config(cfg: Dict[str, Any], path: str = "config.json") -> None:
    safe = DEFAULT_CONFIG.copy()
    safe.update(cfg)
    if safe.get("detection_mode") not in ("live", "file"):
        safe["detection_mode"] = "live"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(safe, f, indent=2)


def is_supported_audio(path: str) -> bool:
    return os.path.splitext(str(path).lower())[1] in SUPPORTED_AUDIO_EXTS


def _band_power(freqs: np.ndarray, mag: np.ndarray, low: float, high: float) -> float:
    mask = (freqs >= low) & (freqs < high)
    if not np.any(mask):
        return 0.0
    return float(np.sum(mag[mask]))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def analyze_audio(audio: np.ndarray, sample_rate: int, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze one audio window and return score + detection features.

    Input audio should be mono float audio in range -1.0 to 1.0.
    """
    if audio is None or len(audio) == 0:
        return {
            "score": 0.0,
            "rms": 0.0,
            "detected": False,
            "error": "empty_audio",
            "bands": {},
        }

    audio = np.asarray(audio, dtype=np.float32).flatten()

    # Remove DC offset.
    audio = audio - float(np.mean(audio))

    # Safety clamp.
    audio = np.clip(audio, -1.0, 1.0)

    rms = float(np.sqrt(np.mean(audio * audio)))

    # Windowing improves FFT stability.
    window = np.hanning(len(audio)).astype(np.float32)
    windowed = audio * window

    mag = np.abs(np.fft.rfft(windowed))
    freqs = np.fft.rfftfreq(len(windowed), d=1.0 / float(sample_rate))

    # Bands chosen for rough chainsaw-like mechanical sound.
    # This is intentionally broad because the user wants any chainsaw-similar
    # engine/mechanical sound to count as valid for forest testing.
    low_band = _band_power(freqs, mag, 40, 180)          # low rumble
    engine_band = _band_power(freqs, mag, 180, 1200)    # engine/harmonics
    chain_band = _band_power(freqs, mag, 1200, 5500)    # chain/teeth/cutting noise
    high_band = _band_power(freqs, mag, 5500, 7800)     # high roughness/noise
    total_band = low_band + engine_band + chain_band + high_band + 1e-9

    engine_ratio = engine_band / total_band
    chain_ratio = chain_band / total_band
    high_ratio = high_band / total_band
    mechanical_ratio = (engine_band + chain_band) / total_band

    # Spectral flatness: higher for noisy rough sound, lower for pure tones.
    # Chainsaws during cutting can be broadband/rough.
    usable = mag[(freqs >= 180) & (freqs <= 6500)] + 1e-12
    spectral_flatness = float(np.exp(np.mean(np.log(usable))) / (np.mean(usable) + 1e-12))

    min_rms = float(cfg.get("min_rms", 0.015))
    # Normalize loudness. A USB mic may differ a lot, so keep configurable.
    # Full score at roughly min_rms*8.
    rms_score = _clamp01((rms - min_rms) / max(min_rms * 7.0, 1e-6))

    # Broad scoring. This intentionally favors any loud mechanical/broadband sound.
    mechanical_score = _clamp01((mechanical_ratio - 0.30) / 0.45)
    chain_score = _clamp01((chain_ratio - 0.10) / 0.40)
    engine_score = _clamp01((engine_ratio - 0.20) / 0.50)
    rough_score = _clamp01((spectral_flatness - 0.05) / 0.35)

    score = 100.0 * (
        0.35 * rms_score +
        0.25 * mechanical_score +
        0.20 * chain_score +
        0.10 * engine_score +
        0.10 * rough_score
    )

    # Hard gate: prevent silent files/noise from triggering.
    enough_loudness = rms >= min_rms
    threshold = float(cfg.get("score_threshold", 60))
    detected = bool(enough_loudness and score >= threshold)

    return {
        "score": round(float(score), 2),
        "rms": round(float(rms), 5),
        "detected": detected,
        "bands": {
            "low": round(low_band, 2),
            "engine": round(engine_band, 2),
            "chain": round(chain_band, 2),
            "high": round(high_band, 2),
            "engine_ratio": round(float(engine_ratio), 3),
            "chain_ratio": round(float(chain_ratio), 3),
            "high_ratio": round(float(high_ratio), 3),
            "mechanical_ratio": round(float(mechanical_ratio), 3),
            "spectral_flatness": round(float(spectral_flatness), 3),
        },
    }


def read_wav_mono(path: str, target_rate: int = 16000) -> Tuple[np.ndarray, int]:
    """
    Read a WAV file using only the Python standard library + numpy.

    Supports 8-bit unsigned PCM and 16-bit signed PCM.
    Stereo/multi-channel files are mixed down to mono.
    If sample rate differs from target_rate, performs simple linear resampling.
    """
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.getnframes()
        raw = wf.readframes(frames)

    if sample_width == 2:
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sample_width == 1:
        audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 3:
        # 24-bit PCM WAV support.
        data = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        signed = (data[:, 0].astype(np.int32) |
                  (data[:, 1].astype(np.int32) << 8) |
                  (data[:, 2].astype(np.int32) << 16))
        signed = np.where(signed & 0x800000, signed - 0x1000000, signed)
        audio = signed.astype(np.float32) / 8388608.0
    elif sample_width == 4:
        audio = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width} bytes")

    if channels > 1:
        audio = audio.reshape(-1, channels)
        audio = np.mean(audio, axis=1)

    if rate != target_rate and len(audio) > 0:
        duration = len(audio) / float(rate)
        old_x = np.linspace(0.0, duration, num=len(audio), endpoint=False)
        new_len = max(1, int(duration * target_rate))
        new_x = np.linspace(0.0, duration, num=new_len, endpoint=False)
        audio = np.interp(new_x, old_x, audio).astype(np.float32)
        rate = target_rate

    return audio.astype(np.float32), rate


def decode_audio_file(path: str, target_rate: int = 16000) -> Tuple[np.ndarray, int]:
    """
    Decode an audio file to mono float32 audio.

    WAV is decoded directly. MP3/M4A/AAC/FLAC/OGG are decoded using ffmpeg.
    The setup script installs ffmpeg automatically.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    if not is_supported_audio(path):
        raise ValueError("Unsupported audio file. Supported: WAV, MP3, M4A, AAC, FLAC, OGG")

    ext = os.path.splitext(path.lower())[1]
    if ext == ".wav":
        try:
            return read_wav_mono(path, target_rate=target_rate)
        except Exception:
            # Some WAV files are compressed. Fall back to ffmpeg.
            pass

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "ffmpeg is required to decode this audio file. Run ./setup.sh again, "
            "or install it manually with: sudo apt install -y ffmpeg"
        )

    cmd = [
        "ffmpeg",
        "-v", "error",
        "-i", path,
        "-ac", "1",
        "-ar", str(int(target_rate)),
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"ffmpeg decode failed: {err or 'unknown error'}")

    audio = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return audio.astype(np.float32), int(target_rate)


def _average_band_features(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not results:
        return {}
    keys = ["engine_ratio", "chain_ratio", "high_ratio", "mechanical_ratio", "spectral_flatness"]
    summary: Dict[str, Any] = {}
    for key in keys:
        vals = [float((r.get("bands") or {}).get(key, 0.0)) for r in results]
        summary[key] = round(float(np.mean(vals)), 3)
    return summary


def analyze_audio_file(path: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze an audio file using the same scoring used for live microphone audio.
    """
    target_rate = int(cfg.get("sample_rate", 16000))
    audio, rate = decode_audio_file(path, target_rate=target_rate)
    window_sec = float(cfg.get("window_sec", 1.0))
    win = max(1, int(rate * window_sec))

    results: List[Dict[str, Any]] = []
    hits = 0
    max_score = 0.0
    best_window: Optional[Dict[str, Any]] = None

    for start in range(0, len(audio), win):
        chunk = audio[start:start + win]
        if len(chunk) < win:
            break
        res = analyze_audio(chunk, rate, cfg)
        res["time_sec"] = round(start / float(rate), 2)
        results.append(res)
        score = float(res.get("score", 0.0))
        if score > max_score:
            max_score = score
            best_window = dict(res)
        if res.get("detected"):
            hits += 1

    history_windows = int(cfg.get("history_windows", 5))
    require_hits = int(cfg.get("require_hits", 3))

    confirmed = False
    first_confirm_time: Optional[float] = None
    for i in range(len(results)):
        window = results[max(0, i - history_windows + 1):i + 1]
        if sum(1 for r in window if r.get("detected")) >= require_hits:
            confirmed = True
            first_confirm_time = float(results[i].get("time_sec", 0.0))
            break

    duration_sec = round(len(audio) / float(rate), 2) if rate else 0.0
    best_window = best_window or {
        "score": 0.0,
        "rms": 0.0,
        "detected": False,
        "bands": {},
        "time_sec": 0.0,
    }

    return {
        "file": os.path.basename(path),
        "path": os.path.abspath(path),
        "confirmed": confirmed,
        "first_confirm_time_sec": first_confirm_time,
        "hits": hits,
        "windows": len(results),
        "duration_sec": duration_sec,
        "sample_rate": rate,
        "max_score": round(float(max_score), 2),
        "average_score": round(float(np.mean([float(r.get("score", 0.0)) for r in results])) if results else 0.0, 2),
        "best_window": best_window,
        "summary_bands": _average_band_features(results),
        "results": results,
    }


def analyze_wav_file(path: str, cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Backward-compatible function name for older app.py versions."""
    return analyze_audio_file(path, cfg)


class ChainsawDetector:
    def __init__(self, cfg: Dict[str, Any], app_dir: str):
        self.cfg = cfg
        self.app_dir = app_dir
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.history = deque(maxlen=int(cfg.get("history_windows", 5)))
        self.last_alert_time = 0.0
        self.event_log = deque(maxlen=50)
        self.status: Dict[str, Any] = {
            "running": False,
            "confirmed_detection": False,
            "instant_detection": False,
            "score": 0.0,
            "rms": 0.0,
            "bands": {},
            "last_update": None,
            "error": None,
            "device": cfg.get("input_device"),
            "alerts_total": 0,
        }

    def update_config(self, cfg: Dict[str, Any]) -> None:
        with self.lock:
            self.cfg.update(cfg)
            self.history = deque(list(self.history), maxlen=int(self.cfg.get("history_windows", 5)))

    def start(self) -> bool:
        with self.lock:
            if self.thread and self.thread.is_alive():
                return False
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.status["running"] = True
            self.status["error"] = None
            self.thread.start()
            return True

    def stop(self) -> bool:
        with self.lock:
            if not self.thread or not self.thread.is_alive():
                self.status["running"] = False
                return False
            self.stop_event.set()
        return True

    def get_status(self) -> Dict[str, Any]:
        with self.lock:
            data = dict(self.status)
            data["history"] = list(self.history)
            data["event_log"] = list(self.event_log)
            data["config"] = dict(self.cfg)
            return data

    def _log_alert(self, score: float, rms: float) -> None:
        log_path = self.cfg.get("log_file", "detections.csv")
        if not os.path.isabs(log_path):
            log_path = os.path.join(self.app_dir, log_path)

        exists = os.path.exists(log_path)
        with open(log_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not exists:
                writer.writerow(["timestamp", "event", "score", "rms"])
            writer.writerow([now_text(), "CHAINSAW_LIKE_SOUND", score, rms])

    def _set_error(self, msg: str) -> None:
        with self.lock:
            self.status["error"] = msg
            self.status["last_update"] = now_text()

    def _loop(self) -> None:
        try:
            import sounddevice as sd
        except Exception as e:
            with self.lock:
                self.status["running"] = False
                self.status["error"] = f"Cannot import sounddevice: {e}"
            return

        while not self.stop_event.is_set():
            try:
                sample_rate = int(self.cfg.get("sample_rate", 16000))
                window_sec = float(self.cfg.get("window_sec", 1.0))
                frames = int(sample_rate * window_sec)
                device = self.cfg.get("input_device", None)
                if device in ["", "None", "null"]:
                    device = None

                audio = sd.rec(
                    frames,
                    samplerate=sample_rate,
                    channels=1,
                    dtype="float32",
                    device=device,
                )
                sd.wait()
                audio = audio.flatten()

                res = analyze_audio(audio, sample_rate, self.cfg)
                instant = bool(res.get("detected", False))

                with self.lock:
                    self.history.append(instant)
                    require_hits = int(self.cfg.get("require_hits", 3))
                    hits = sum(1 for x in self.history if x)
                    confirmed = hits >= require_hits
                    self.status.update({
                        "running": True,
                        "instant_detection": instant,
                        "confirmed_detection": confirmed,
                        "score": res.get("score", 0.0),
                        "rms": res.get("rms", 0.0),
                        "bands": res.get("bands", {}),
                        "last_update": now_text(),
                        "error": None,
                        "device": device,
                    })

                if confirmed:
                    now = time.time()
                    cooldown = float(self.cfg.get("cooldown_sec", 30))
                    if now - self.last_alert_time >= cooldown:
                        self.last_alert_time = now
                        with self.lock:
                            self.status["alerts_total"] = int(self.status.get("alerts_total", 0)) + 1
                            self.event_log.appendleft({
                                "time": now_text(),
                                "event": "CHAINSAW-LIKE SOUND DETECTED",
                                "score": res.get("score", 0.0),
                                "rms": res.get("rms", 0.0),
                            })
                        self._log_alert(float(res.get("score", 0.0)), float(res.get("rms", 0.0)))

            except Exception as e:
                self._set_error(str(e))
                time.sleep(2.0)

        with self.lock:
            self.status["running"] = False
            self.status["confirmed_detection"] = False
            self.status["instant_detection"] = False
            self.status["last_update"] = now_text()
