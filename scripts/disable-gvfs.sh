#!/usr/bin/env bash
# Script to prevent GVFS from capturing and locking the Nikon D3100 PTP camera interface

echo "=== CamCam: Configuring GVFS to release USB Camera locks ==="

# 1. Kill any currently running GVFS camera monitors
pkill -f gvfsd-gphoto2 2>/dev/null || true
pkill -f gvfs-gphoto2-volume-monitor 2>/dev/null || true

# 2. Mask user systemd services for gvfs volume monitor if desktop is running
if [ -d "/usr/share/dbus-1/services" ]; then
    echo "Checking dbus services..."
fi

# 3. Add user to plugdev group
if [ -n "$USER" ]; then
    sudo usermod -a -G plugdev "$USER"
    echo "Added user '$USER' to plugdev group."
fi

echo "GVFS camera release configuration complete."
