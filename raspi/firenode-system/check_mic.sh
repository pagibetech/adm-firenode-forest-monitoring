#!/bin/bash
echo "=== ALSA Recording Devices ==="
arecord -l || true

echo ""
echo "=== Python sounddevice input devices ==="
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$APP_DIR/venv/bin/python" ]; then
  PY="$APP_DIR/venv/bin/python"
else
  PY="python3"
fi
"$PY" - <<'PY'
try:
    import sounddevice as sd
    devices = sd.query_devices()
    found = False
    for idx, dev in enumerate(devices):
        if int(dev.get('max_input_channels', 0)) > 0:
            found = True
            print(f"ID {idx}: {dev.get('name')} | inputs={dev.get('max_input_channels')} | default_rate={dev.get('default_samplerate')}")
    if not found:
        print("No Python sounddevice input devices found.")
except Exception as e:
    print("sounddevice error:", e)
PY
