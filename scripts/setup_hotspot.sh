#!/usr/bin/env bash
# ==============================================================================
# CamCam - Standalone Wi-Fi Hotspot (AP Mode) Setup for Raspberry Pi
# Allows you to connect your phone/laptop directly to the Raspberry Pi in the
# field with zero internet connection or external routers.
#
# Default SSID:     CamCam-WiFi
# Default Password: camcam1234
# Fixed URL:        http://10.42.0.1:8000  (or http://camcam.local:8000)
# ==============================================================================

set -e

HOTSPOT_SSID="${1:-CamCam-WiFi}"
HOTSPOT_PASS="${2:-camcam1234}"

echo "================================================================="
echo "   📡 CamCam - Standalone Wi-Fi Hotspot Setup"
echo "================================================================="
echo "SSID:     $HOTSPOT_SSID"
echo "Password: $HOTSPOT_PASS"
echo "URL:      http://10.42.0.1:8000 (or http://camcam.local:8000)"
echo "================================================================="

if [ "$EUID" -ne 0 ]; then
    echo "[!] Please run this script with sudo: sudo ./scripts/setup_hotspot.sh"
    exit 1
fi

# Ensure Wi-Fi is unblocked
echo "[*] Unblocking Wi-Fi radio..."
rfkill unblock wifi 2>/dev/null || true

# Find wireless interface
WLAN_IF=$(iw dev | awk '$1=="Interface"{print $2}' | head -n 1)
if [ -z "$WLAN_IF" ]; then
    WLAN_IF="wlan0"
fi
echo "[*] Using Wi-Fi interface: $WLAN_IF"

# Detect if NetworkManager (nmcli) is available (Standard on Raspberry Pi OS Bookworm & Bullseye)
if command -v nmcli >/dev/null 2>&1; then
    echo "[*] Configuring official NetworkManager native hotspot..."

    # Delete existing hotspot profile if it was partially configured
    nmcli connection delete "Hotspot" 2>/dev/null || true
    nmcli connection delete "CamCam-Hotspot" 2>/dev/null || true
    nmcli connection delete "$HOTSPOT_SSID" 2>/dev/null || true

    # Create & activate native WPA2-PSK Hotspot (Auto-configures standard 10.42.0.1 DHCP server)
    nmcli device wifi hotspot ifname "$WLAN_IF" ssid "$HOTSPOT_SSID" password "$HOTSPOT_PASS"

    HOTSPOT_IP="10.42.0.1"

else
    # Fallback for legacy Raspberry Pi OS (dhcpcd + hostapd + dnsmasq)
    echo "[*] Configuring hostapd & dnsmasq fallback..."
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

echo ""
echo "================================================================="
echo "   🎉 CamCam Wi-Fi Hotspot is now BROADCASTING!"
echo "================================================================="
echo "1. On your phone: Go to Wi-Fi settings"
echo "2. Connect to:    '$HOTSPOT_SSID'"
echo "3. Password:      '$HOTSPOT_PASS'"
echo "4. Open Browser:  http://$HOTSPOT_IP:8000"
echo "                  (or http://camcam.local:8000)"
echo ""
echo "Troubleshooting Tips if phone doesn't connect:"
echo " - 'Forget' any existing '$HOTSPOT_SSID' saved on your phone."
echo " - Turn off 'Mobile Data / 4G / 5G' on your phone while testing."
echo " - If prompted 'No Internet', select 'Stay Connected'."
echo "================================================================="
