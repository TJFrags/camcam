#!/usr/bin/env bash
# ==============================================================================
# CamCam - Standalone Wi-Fi Hotspot (AP Mode) Setup for Raspberry Pi
# Allows you to connect your phone/laptop directly to the Raspberry Pi in the
# field with zero internet connection or external routers.
#
# Default SSID:     CamCam-WiFi
# Default Password: camcam1234
# Fixed URL:        http://192.168.4.1:8000  (or http://camcam.local:8000)
# ==============================================================================

set -e

HOTSPOT_SSID="${1:-CamCam-WiFi}"
HOTSPOT_PASS="${2:-camcam1234}"
HOTSPOT_IP="192.168.4.1/24"
CON_NAME="CamCam-Hotspot"

echo "================================================================="
echo "   📡 CamCam - Standalone Wi-Fi Hotspot Setup"
echo "================================================================="
echo "SSID:     $HOTSPOT_SSID"
echo "Password: $HOTSPOT_PASS"
echo "Fixed IP: 192.168.4.1"
echo "URL:      http://192.168.4.1:8000 (or http://camcam.local:8000)"
echo "================================================================="

if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run this script with sudo: sudo ./scripts/setup_hotspot.sh"
    exit 1
fi

# Detect if NetworkManager (nmcli) is active (standard on Raspberry Pi OS Bookworm & Bullseye)
if command -v nmcli >/dev/null 2>&1; then
    echo "[*] Using NetworkManager (nmcli)..."

    # Remove existing CamCam hotspot connection if present
    nmcli connection delete "$CON_NAME" 2>/dev/null || true

    # Find wireless interface (default wlan0)
    WLAN_IF=$(nmcli device status | awk '$2=="wifi" {print $1}' | head -n 1)
    if [ -z "$WLAN_IF" ]; then
        WLAN_IF="wlan0"
    fi

    echo "[*] Creating Wi-Fi Access Point on interface '$WLAN_IF'..."
    nmcli connection add type wifi ifname "$WLAN_IF" con-name "$CON_NAME" autoconnect yes ssid "$HOTSPOT_SSID"
    nmcli connection modify "$CON_NAME" 802-11-wireless.mode ap 802-11-wireless.band bg
    nmcli connection modify "$CON_NAME" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$HOTSPOT_PASS"
    nmcli connection modify "$CON_NAME" ipv4.method shared ipv4.addresses "$HOTSPOT_IP"

    # Activate hotspot
    echo "[*] Activating Hotspot '$HOTSPOT_SSID'..."
    nmcli connection up "$CON_NAME"

else
    # Fallback to hostapd + dnsmasq for legacy distributions
    echo "[*] Setting up hostapd & dnsmasq fallback..."
    apt-get update && apt-get install -y hostapd dnsmasq

    # Stop services while configuring
    systemctl stop hostapd || true
    systemctl stop dnsmasq || true

    # Configure static IP on wlan0 in dhcpcd.conf if dhcpcd exists
    if [ -f /etc/dhcpcd.conf ]; then
        if ! grep -q "interface wlan0" /etc/dhcpcd.conf; then
            cat <<EOF >> /etc/dhcpcd.conf

# CamCam Hotspot Static IP
interface wlan0
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF
        fi
    fi

    # Configure dnsmasq
    cat <<EOF > /etc/dnsmasq.d/camcam-hotspot.conf
interface=wlan0
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,24h
address=/camcam.local/192.168.4.1
address=/cam.box/192.168.4.1
EOF

    # Configure hostapd
    cat <<EOF > /etc/hostapd/hostapd.conf
interface=wlan0
driver=nl80211
ssid=$HOTSPOT_SSID
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=$HOTSPOT_PASS
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

    sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd || true

    systemctl unmask hostapd
    systemctl enable hostapd dnsmasq
    systemctl restart dhcpcd || true
    systemctl start dnsmasq
    systemctl start hostapd
fi

# Optional port 80 -> 8000 redirect so typing http://192.168.4.1 works without :8000
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8000 2>/dev/null || true

echo ""
echo "================================================================="
echo "   ✅ CamCam Hotspot is ACTIVE!"
echo "================================================================="
echo "1. On your phone/laptop, join Wi-Fi network: '$HOTSPOT_SSID'"
echo "2. Wi-Fi Password: '$HOTSPOT_PASS'"
echo "3. Open your browser to:"
echo "      http://192.168.4.1:8000"
echo "   or http://camcam.local:8000"
echo ""
echo "To switch back to your home Wi-Fi:"
echo "   sudo nmcli connection up <Your-Home-WiFi-Name>"
echo "================================================================="
