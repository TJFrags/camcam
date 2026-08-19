# 📷 CamCam - Nikon D3100 Shutter Release & Quick Settings Suite

CamCam turns your PC or Raspberry Pi into a **Remote Shutter Trigger & Quick Settings Suite** for your **Nikon D3100 DSLR** over **Wired USB (PTP)**.

> **Storage Mode:** 100% Direct to Camera SD Card. **0 bytes are saved or stored on the computer.**

---

## 🌟 Highlights

- ⚡ **Streamlined Quick Settings**: 1-tap selectors for **ISO** (Auto, 100–6400), **Shutter Speed** (1/4000s–2s), **Aperture** (f/1.8–f/22), **Exposure Compensation**, and **Self-Timer** countdowns.
- 🎯 **Shooting Presets**: Instant configuration for `Auto`, `Action`, `Portrait`, `Landscape`, `Night`, and `Studio`.
- 📱 **FastAPI Web Remote**: Open `http://localhost:8000` (or `http://<YOUR_IP>:8000`) on any phone, tablet, or PC on your network.
- 📸 **Zero Disk Usage on Computer**: All photos are stored directly on the camera's inserted SD card.
- ⏱️ **Automated Intervalometer / Timelapse**: Continuous or fixed-target timelapse sequences with live progress monitoring.
- 🔌 **100% Wired USB Stability**: Pure wired USB PTP communication (via `digiCamControl` on Windows and `gphoto2` on Linux/Raspberry Pi).

---

## 📷 Critical Camera Setup Checklist (Before First Shot)

1. **Focus Switch ➜ `M` (Manual Focus)** on the lens barrel (in Autofocus mode, the camera will refuse to fire over USB if it cannot lock focus).
2. **Mode Dial ➜ `M`, `A`, `S`, or `P`** (Avoid `AUTO` or Guide modes, which disable USB PTP commands).
3. **SD Card**: Insert an SD card (photos are stored directly to the card).
4. **Connect via USB**: Connect the Mini-USB cable directly to your PC/Raspberry Pi and turn camera **ON**.

---

## 🚀 Quick Start

### 1. Launch the Web Shutter & Quick Settings Dashboard:
```powershell
python -m camcam serve
```
Open **`http://localhost:8000`** in your browser!

### 2. Command Line Interface (CLI):

#### Trigger a Single Shot:
```powershell
python take_picture.py
# or
python -m camcam shutter
```

#### Shoot with Quick Settings:
```powershell
# Using a preset
python -m camcam shutter --preset action

# Explicit settings (ISO 400, 1/500s shutter, f/4 aperture)
python -m camcam shutter --iso 400 --shutter 1/500 --aperture 4.0

# 5-second self-timer countdown
python take_picture.py --delay 5

# Rapid 3-shot burst
python -m camcam shutter --count 3
```

#### Automated Timelapse Intervalometer:
```powershell
# Trigger every 5 seconds for 100 frames
python -m camcam timelapse --interval 5.0 --count 100
```
