#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Test a Raspberry Pi USB camera using the FireNode capture settings.")
    parser.add_argument("--device", type=int, default=0, help="Video device index, for example 0 for /dev/video0.")
    parser.add_argument("--fourcc", default="MJPG", help="Camera FOURCC format. Default: MJPG.")
    parser.add_argument("--width", type=int, default=640, help="Frame width. Default: 640.")
    parser.add_argument("--height", type=int, default=480, help="Frame height. Default: 480.")
    parser.add_argument("--fps", type=int, default=25, help="Requested FPS. Default: 25.")
    parser.add_argument("--warmup", type=int, default=5, help="Frames to discard after opening. Default: 5.")
    parser.add_argument("--frames", type=int, default=20, help="Frames to read for the test. Default: 20.")
    parser.add_argument("--output", default="/tmp/firenode_camera_test.jpg", help="Path to save a test JPEG.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import cv2
    except Exception as exc:
        print(f"ERROR: cv2/OpenCV is not available: {exc}", file=sys.stderr)
        return 1

    device_path = f"/dev/video{args.device}"
    device = device_path if os.path.exists(device_path) else args.device
    fourcc = (args.fourcc or "MJPG").strip().upper()[:4]

    print(f"Opening camera: {device}")
    print(f"Backend: V4L2")
    print(f"Format: {fourcc} {args.width}x{args.height} @ {args.fps} FPS")

    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cap.isOpened():
        print(f"ERROR: cannot open {device}", file=sys.stderr)
        return 1

    try:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        cap.set(cv2.CAP_PROP_FPS, args.fps)

        for _ in range(max(0, args.warmup)):
            cap.read()

        last_frame = None
        ok_count = 0
        start = time.time()
        for _ in range(max(1, args.frames)):
            ok, frame = cap.read()
            if ok and frame is not None:
                ok_count += 1
                last_frame = frame
            time.sleep(0.01)

        elapsed = max(0.001, time.time() - start)
        print(f"Frames read: {ok_count}/{args.frames} in {elapsed:.2f}s")
        print(f"Actual width: {cap.get(cv2.CAP_PROP_FRAME_WIDTH):.0f}")
        print(f"Actual height: {cap.get(cv2.CAP_PROP_FRAME_HEIGHT):.0f}")
        print(f"Actual FPS: {cap.get(cv2.CAP_PROP_FPS):.1f}")

        if ok_count <= 0 or last_frame is None:
            print("ERROR: no frames read", file=sys.stderr)
            return 2

        if not cv2.imwrite(args.output, last_frame):
            print(f"ERROR: could not save {args.output}", file=sys.stderr)
            return 3

        print(f"Saved test frame: {args.output}")
        print("Camera test passed.")
        return 0
    finally:
        cap.release()


if __name__ == "__main__":
    raise SystemExit(main())
