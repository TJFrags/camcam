#!/usr/bin/env bash
# ==============================================================================
# CamCam - Turnkey Installer for Raspberry Pi 4 (Raspberry Pi OS)
# Sets up Nikon D3100 PTP USB drivers, udev rules, Python venv, & systemd service
# ==============================================================================

set -e

echo "================================================================="
echo "   📷 CamCam - Nikon D3100 Quick Settings & Remote for RPi 4"
echo "================================================================="

# 1. Update and install required OS packages
echo "[1/6] Installing system dependencies (gphoto2, libgphoto2, libusb)..."
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    gphoto2 \
    libgphoto2-dev \
    libgphoto2-6 \
    libusb-1.0-0-dev \
    libjpeg-dev \
    zlib1g-dev

# 2. Configure udev rules for Nikon D3100 (Vendor 04b0, Product 0427)
echo "[2/6] Setting up udev rules for Nikon D3100 USB communication..."
sudo tee /etc/udev/rules.d/99-nikon-d3100.rules > /dev/null <<'EOF'
# Udev rule for Nikon D3100 DSLR PTP USB communication
SUBSYSTEM=="usb", ATTR{idVendor}=="04b0", ATTR{idProduct}=="0427", MODE="0666", GROUP="plugdev", ENV{ID_GPHOTO2}="1", ENV{GPHOTO2_DRIVER}="PTP"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="04b0", ATTR{idProduct}=="0427", RUN+="/usr/bin/pkill -9 -f gvfsd-gphoto2"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

# 3. Add current user to plugdev group
echo "[3/6] Adding user '$USER' to plugdev group..."
sudo usermod -a -G plugdev "$USER"

# 4. Disable GVFS auto-mount interference
echo "[4/6] Killing any conflicting GVFS camera background locks..."
pkill -9 -f gvfsd-gphoto2 2>/dev/null || true
pkill -9 -f gvfs-gphoto2-volume-monitor 2>/dev/null || true

# 5. Create Python Virtual Environment & install dependencies
echo "[5/6] Setting up Python virtual environment and dependencies..."
INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ ! -d "$INSTALL_DIR/venv" ]; then
    python3 -m venv "$INSTALL_DIR/venv"
fi

source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip setuptools wheel
pip install -r "$INSTALL_DIR/requirements.txt"

# Install python-gphoto2 binary if available
echo "Attempting to install python-gphoto2 native bindings..."
pip install gphoto2 || echo "[Note] python-gphoto2 native wheel skipped; high-speed CLI backend will be used automatically."

pip install -e "$INSTALL_DIR"

# 6. Configure systemd auto-start service
echo "[6/6] Configuring optional systemd background service..."
sudo tee /etc/systemd/system/camcam.service > /dev/null <<EOF
[Unit]
Description=CamCam Nikon D3100 Remote Shutter Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/venv/bin/python3 -m camcam serve --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload

echo "================================================================="
echo "   🎉 Raspberry Pi 4 Setup Complete!"
echo "================================================================="
echo ""
echo "Camera Checklist for Nikon D3100:"
echo " 1. Lens focus switch: set to 'M' (Manual Focus)."
echo " 2. Mode dial: set to 'M', 'A', 'S', or 'P'."
echo " 3. Connect Nikon D3100 to RPi 4 USB 3.0 / 2.0 port & turn camera ON."
echo ""
echo "To start CamCam Web Remote manually:"
echo "   source $INSTALL_DIR/venv/bin/activate"
echo "   python3 -m camcam serve"
echo ""
echo "Then open your phone or PC browser to:"
echo "   http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "To enable automatic startup on Raspberry Pi boot:"
echo "   sudo systemctl enable --now camcam"
echo "================================================================="
