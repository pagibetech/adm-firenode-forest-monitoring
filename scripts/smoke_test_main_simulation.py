#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://127.0.0.1:8090"


def fetch_json(path: str) -> dict:
    with urllib.request.urlopen(BASE_URL + path, timeout=8) as res:
        return json.loads(res.read().decode("utf-8"))


def wait_for_server(proc: subprocess.Popen, timeout_sec: float = 20.0) -> None:
    deadline = time.time() + timeout_sec
    last_error = ""
    while time.time() < deadline:
        if proc.poll() is not None:
            out, _ = proc.communicate(timeout=1)
            raise RuntimeError(f"simulation exited early with code {proc.returncode}\n{out}")
        try:
            with urllib.request.urlopen(BASE_URL + "/", timeout=2) as res:
                if res.status == 200:
                    return
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"simulation did not become ready: {last_error}")


def main() -> int:
    script = ROOT / "scripts" / "start_main_simulation.sh"
    proc = subprocess.Popen(
        [str(script)],
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        wait_for_server(proc)
        dashboard = fetch_json("/api/server-dashboard")
        lora = fetch_json("/api/lora/status")
        recordings = fetch_json("/api/recordings")

        all_nodes = dashboard.get("all_nodes") or []
        if len(all_nodes) != 4:
            raise AssertionError(f"expected 4 dashboard nodes, got {len(all_nodes)}")
        if lora.get("active_nodes") != 4:
            raise AssertionError(f"expected 4 active LoRa nodes, got {lora.get('active_nodes')}")
        local_camera = (all_nodes[0].get("camera") or {})
        if not local_camera.get("running"):
            raise AssertionError("local camera stream is not running")
        if not isinstance(recordings.get("recordings"), list):
            raise AssertionError("/api/recordings did not return a list")

        print("Smoke test passed")
        print(f"dashboard_nodes={len(all_nodes)}")
        print(f"lora_active_nodes={lora.get('active_nodes')}")
        print(f"stored_packet_count={lora.get('stored_packet_count')}")
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
