#!/bin/bash
set -e
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

INSTALL_SERVICE="no"
if [ "${1:-}" = "--install-service" ]; then
  INSTALL_SERVICE="yes"
fi

export DEBIAN_FRONTEND=noninteractive

echo "============================================================"
echo " FireNode RPi Unified Main Server / Node Setup"
echo " Target: Raspberry Pi OS Legacy Lite 32-bit / RPi 3B"
echo " Version: setup v2.0 - manual start by default"
echo "============================================================"

echo "[1/7] Updating apt package lists..."
sudo apt update

echo "[2/7] Installing Raspberry Pi system packages..."
# Keep heavy packages such as numpy/opencv from apt. Avoid building them with pip on RPi 3B.
sudo apt install -y \
  python3 python3-pip python3-venv python3-dev python3-flask python3-requests python3-numpy \
  python3-opencv python3-cffi python3-pil python3-smbus \
  ffmpeg portaudio19-dev libportaudio2 libportaudiocpp0 libasound2-dev libffi-dev \
  libatlas-base-dev alsa-utils v4l-utils i2c-tools \
  net-tools curl build-essential

echo "[3/7] Enabling I2C for MLX90640 thermal camera..."
if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_i2c 0 || true
fi

echo "[4/7] Creating Python virtual environment..."
# Create a venv that can see apt-installed packages. This avoids slow numpy/opencv builds on RPi 3B.
if [ ! -d "$APP_DIR/venv" ]; then
  python3 -m venv --system-site-packages "$APP_DIR/venv"
fi

PY="$APP_DIR/venv/bin/python"
PIP="$APP_DIR/venv/bin/pip"

echo "[5/7] Updating pip tools inside venv..."
"$PY" -m pip install --upgrade pip setuptools wheel || true

echo "[6/7] Checking / installing Python dependencies..."
# Install sounddevice using pip because apt package name varies / may be missing.
if ! "$PY" - <<'PY'
try:
    import sounddevice
except Exception:
    raise SystemExit(1)
print("sounddevice already available.")
PY
then
  echo "Installing Python sounddevice module through pip..."
  "$PIP" install --no-cache-dir --prefer-binary sounddevice cffi
fi

# Install Adafruit MLX90640 stack if missing. The main app can still run without it using thermal simulation,
# but installing it here makes the thermal camera ready after reboot/wiring.
if ! "$PY" - <<'PY'
try:
    import board
    import busio
    import adafruit_mlx90640
except Exception:
    raise SystemExit(1)
print("Adafruit MLX90640 libraries already available.")
PY
then
  echo "Installing Adafruit Blinka + MLX90640 Python libraries..."
  "$PIP" install --no-cache-dir --prefer-binary adafruit-blinka adafruit-circuitpython-mlx90640 || true
fi

# Check the required modules. If Flask/requests are missing from apt, install only those lightweight packages.
MISSING="$($PY - <<'PY'
mods = ["flask", "requests", "numpy", "cv2", "sounddevice", "PIL"]
missing = []
for mod in mods:
    try:
        __import__(mod)
    except Exception:
        missing.append(mod)
print(" ".join(missing))
PY
)"

if [ -n "$MISSING" ]; then
  echo "Missing Python modules after apt/pip install: $MISSING"
  echo "Trying fallback pip install for lightweight modules..."
  case " $MISSING " in
    *" flask "*) "$PIP" install --no-cache-dir --prefer-binary Flask ;;
  esac
  case " $MISSING " in
    *" requests "*) "$PIP" install --no-cache-dir --prefer-binary requests ;;
  esac
  case " $MISSING " in
    *" sounddevice "*) "$PIP" install --no-cache-dir --prefer-binary sounddevice cffi ;;
  esac
  case " $MISSING " in
    *" PIL "*) "$PIP" install --no-cache-dir --prefer-binary Pillow ;;
  esac
fi

# Final check. Do not try to pip-build numpy/opencv on RPi 3B because it can take too long.
"$PY" - <<'PY'
required = {
    "flask": "Flask web server",
    "requests": "HTTP client",
    "numpy": "audio/thermal/math processing",
    "cv2": "USB camera / OpenCV",
    "sounddevice": "USB microphone audio input",
    "PIL": "thermal image output",
}
missing = []
for mod, desc in required.items():
    try:
        __import__(mod)
    except Exception as e:
        missing.append(f"{mod} ({desc}): {e}")
if missing:
    print("ERROR: Required Python modules are still missing:")
    for item in missing:
        print(" - " + item)
    print("\nFor numpy/cv2/PIL, install through apt where possible on Raspberry Pi 3B:")
    print("sudo apt install -y python3-numpy python3-opencv python3-pil")
    raise SystemExit(1)
print("Python dependency check passed.")

optional = ["board", "busio", "adafruit_mlx90640"]
missing_optional = []
for mod in optional:
    try:
        __import__(mod)
    except Exception as e:
        missing_optional.append(f"{mod}: {e}")
if missing_optional:
    print("WARNING: MLX90640 optional libraries are missing. Thermal simulation will still work.")
    for item in missing_optional:
        print(" - " + item)
else:
    print("MLX90640 Python library check passed.")
PY

echo "[7/7] Preparing app files..."
mkdir -p logs
chmod +x run.sh check_mic.sh install_service.sh uninstall_service.sh setup.sh

if [ "$INSTALL_SERVICE" = "yes" ]; then
  echo "Optional autostart requested through --install-service."
  ./install_service.sh
else
  echo "Autostart service was NOT installed. This app will run only when you manually execute ./run.sh"
  echo "If an old autostart service exists, remove it with: ./uninstall_service.sh"
fi

IP_ADDR="$(hostname -I | awk '{print $1}')"
echo ""
echo "============================================================"
echo " Setup complete."
echo " Open the web GUI from another device: http://${IP_ADDR}:8090"
echo " Manual run command: ./run.sh"
echo " Autostart service: NOT installed by default"
echo " Check USB mic: ./check_mic.sh"
echo " Check MLX90640 address: i2cdetect -y 1"
echo "============================================================"
