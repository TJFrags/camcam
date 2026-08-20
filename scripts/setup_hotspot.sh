#!/usr/bin/env bash
# ==============================================================================
# CamCam - Standalone Wi-Fi Hotspot (AP Mode) Setup for Raspberry Pi
# Allows you to connect your phone/laptop directly to the Raspberry Pi in the
# field with zero internet connection or external routers.
#
# Default SSID:     CamCam-WiFi
# Default Password: camcam1234
# Fixed URL:        http://camcam (or http://camcam.local:8000, http://cam.box)
# ==============================================================================

set -e

HOTSPOT_SSID="${1:-CamCam-WiFi}"
HOTSPOT_PASS="${2:-camcam1234}"

echo "================================================================="
echo "   📡 CamCam - Standalone Wi-Fi Hotspot & Custom URL Setup"
echo "================================================================="
echo "SSID:     $HOTSPOT_SSID"
echo "Password: $HOTSPOT_PASS"
echo "URL:      http://camcam (or http://cam.box, http://10.42.0.1:8000)"
echo "================================================================="

if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run this script with sudo: sudo ./scripts/setup_hotspot.sh"
    exit 1
fi

# 1. Set System Hostname to camcam
echo "[1/5] Setting system hostname to 'camcam'..."
hostnamectl set-hostname camcam || true
if ! grep -q "127.0.1.1.*camcam" /etc/hosts; then
    echo "127.0.1.1 camcam" >> /etc/hosts
fi

# 2. Ensure Wi-Fi is unblocked
echo "[2/5] Unblocking Wi-Fi radio..."
rfkill unblock wifi 2>/dev/null || true

# 3. Find wireless interface
WLAN_IF=$(iw dev | awk '$1=="Interface"{print $2}' | head -n 1)
if [ -z "$WLAN_IF" ]; then
    WLAN_IF="wlan0"
fi
echo "[*] Using Wi-Fi interface: $WLAN_IF"

# 4. Configure DNS name mapping (camcam, cam.box -> Hotspot IP)
echo "[3/5] Configuring local DNS entries for http://camcam and http://cam.box..."
mkdir -p /etc/NetworkManager/dnsmasq-shared.d 2>/dev/null || true
cat <<EOF > /etc/NetworkManager/dnsmasq-shared.d/camcam.conf 2>/dev/null || true
address=/camcam/10.42.0.1
address=/camcam.local/10.42.0.1
address=/cam.box/10.42.0.1
EOF

# Restart Avahi mDNS daemon if present
if command -v avahi-daemon >/dev/null 2>&1; then
    systemctl restart avahi-daemon 2>/dev/null || true
fi

# 5. Detect if NetworkManager (nmcli) is available (Standard on Raspberry Pi OS Bookworm & Bullseye)
if command -v nmcli >/dev/null 2>&1; then
    echo "[4/5] Configuring official NetworkManager native hotspot..."

    # Delete existing hotspot profile if it was partially configured
    nmcli connection delete "Hotspot" 2>/dev/null || true
    nmcli connection delete "CamCam-Hotspot" 2>/dev/null || true
    nmcli connection delete "$HOTSPOT_SSID" 2>/dev/null || true

    # Create & activate native WPA2-PSK Hotspot (Auto-configures standard 10.42.0.1 DHCP server)
    nmcli device wifi hotspot ifname "$WLAN_IF" ssid "$HOTSPOT_SSID" password "$HOTSPOT_PASS"

    HOTSPOT_IP="10.42.0.1"

else
    # Fallback for legacy Raspberry Pi OS (dhcpcd + hostapd + dnsmasq)
    echo "[4/5] Configuring hostapd & dnsmasq fallback..."
    apt-get update && apt-get install -y hostapd dnsmasq

    systemctl stop hostapd || true
    systemctl stop dnsmasq || true

    # Configure static IP on wlan0 in dhcpcd.conf
    if [ -f /etc/dhcpcd.conf ]; then
        if ! grep -q "interface $WLAN_IF" /etc/dhcpcd.conf; then
            cat <<EOF >> /etc/dhcpcd.conf

# CamCam Hotspot Static IP
interface $WLAN_IF
    static ip_address=192.168.4.1/24
    nohook wpa_supplicant
EOF
        fi
    fi

    # Configure dnsmasq
    cat <<EOF > /etc/dnsmasq.d/camcam-hotspot.conf
interface=$WLAN_IF
dhcp-range=192.168.4.10,192.168.4.50,255.255.255.0,24h
address=/camcam/192.168.4.1
address=/camcam.local/192.168.4.1
address=/cam.box/192.168.4.1
EOF

    # Configure hostapd
    cat <<EOF > /etc/hostapd/hostapd.conf
interface=$WLAN_IF
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
wpa_pairwise=CCMP
rsn_pairwise=CCMP
EOF

    sed -i 's|#DAEMON_CONF=""|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd || true

    systemctl unmask hostapd
    systemctl enable hostapd dnsmasq
    systemctl restart dhcpcd || true
    systemctl restart dnsmasq
    systemctl restart hostapd

    HOTSPOT_IP="192.168.4.1"
fi

# 6. Setup port 80 -> 8000 forwarding so you don't even need to type :8000
echo "[5/5] Enabling Port 80 -> Port 8000 automatic redirect..."
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 8000 2>/dev/null || true

echo ""
echo "================================================================="
echo "   🎉 Custom URL Setup Complete!"
echo "================================================================="
echo "1. Connect your phone to: '$HOTSPOT_SSID' (Pass: '$HOTSPOT_PASS')"
echo "2. In your phone's browser, open ANY of these:"
echo ""
echo "      http://camcam"
echo "      http://cam.box"
echo "      http://camcam.local:8000"
echo "      http://$HOTSPOT_IP:8000"
echo ""
echo "Tip: On mobile Chrome, type 'http://camcam/' with the trailing slash"
echo "     so Chrome doesn't treat it as a Google Search query."
echo "================================================================="
