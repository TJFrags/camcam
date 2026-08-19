"""
CamCam REST API Routes (Shutter Remote & Quick Settings Only)
"""

import platform
import psutil
import sys
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from camcam.engine.camera_manager import CameraManager
from camcam.engine.timelapse import TimelapseEngine

router = APIRouter(prefix="/api")

# Singleton managers
camera_manager = CameraManager()
timelapse_engine = TimelapseEngine(camera_manager)


# ==============================================================================
# Pydantic Schemas
# ==============================================================================

class SettingsUpdateRequest(BaseModel):
    iso: Optional[str] = None
    shutterspeed: Optional[str] = None
    aperture: Optional[str] = None
    exposurecompensation: Optional[str] = None
    whitebalance: Optional[str] = None
    preset: Optional[str] = None


class ShutterTriggerRequest(BaseModel):
    delay: float = Field(default=0.0, ge=0.0, le=60.0)
    settings: Optional[Dict[str, Any]] = None


class BurstTriggerRequest(BaseModel):
    count: int = Field(default=3, ge=1, le=20)
    delay_between: float = Field(default=0.2, ge=0.0, le=10.0)
    settings: Optional[Dict[str, Any]] = None


class TimelapseStartRequest(BaseModel):
    interval: float = Field(default=5.0, ge=0.5, le=3600.0)
    count: int = Field(default=0, ge=0, le=10000)


# ==============================================================================
# Camera & Settings Endpoints
# ==============================================================================

@router.get("/camera/status")
def get_camera_status():
    status_obj = camera_manager.get_status()
    return {
        "connected": status_obj.connected,
        "model": status_obj.model,
        "port": status_obj.port,
        "battery_level": status_obj.battery_level,
        "storage_target": status_obj.storage_target,
        "ready": status_obj.ready,
        "backend": status_obj.backend_name,
        "message": status_obj.message,
    }


@router.post("/camera/connect")
def connect_camera():
    success = camera_manager.connect()
    status_obj = camera_manager.get_status()
    return {
        "success": success,
        "connected": status_obj.connected,
        "model": status_obj.model,
        "message": status_obj.message,
    }


@router.get("/camera/settings")
def get_camera_settings():
    return camera_manager.get_config()


@router.post("/camera/settings")
def update_camera_settings(req: SettingsUpdateRequest):
    if req.preset:
        if not camera_manager.apply_preset(req.preset):
            raise HTTPException(status_code=400, detail=f"Unknown preset '{req.preset}'")
        return {"success": True, "applied_preset": req.preset, "settings": camera_manager.get_config()}

    updates = {}
    if req.iso is not None:
        camera_manager.set_config("iso", str(req.iso))
        updates["iso"] = req.iso
    if req.shutterspeed is not None:
        camera_manager.set_config("shutterspeed", str(req.shutterspeed))
        updates["shutterspeed"] = req.shutterspeed
    if req.aperture is not None:
        camera_manager.set_config("aperture", str(req.aperture))
        updates["aperture"] = req.aperture
    if req.exposurecompensation is not None:
        camera_manager.set_config("exposurecompensation", str(req.exposurecompensation))
        updates["exposurecompensation"] = req.exposurecompensation
    if req.whitebalance is not None:
        camera_manager.set_config("whitebalance", str(req.whitebalance))
        updates["whitebalance"] = req.whitebalance

    return {"success": True, "updated": updates, "settings": camera_manager.get_config()}


# ==============================================================================
# Shutter & Capture Endpoints (Trigger Shutter Directly to Camera SD Card)
# ==============================================================================

@router.post("/shutter/trigger")
def trigger_shutter(req: ShutterTriggerRequest):
    try:
        clean_settings = {k: str(v) for k, v in req.settings.items()} if req.settings else None
        res = camera_manager.capture_image(
            delay=req.delay,
            settings=clean_settings
        )
        if not res.success:
            raise HTTPException(status_code=500, detail=res.error_message or "Shutter trigger failed")

        return {
            "success": True,
            "message": res.message,
            "timestamp": res.timestamp,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/shutter/burst")
def trigger_burst(req: BurstTriggerRequest):
    try:
        clean_settings = {k: str(v) for k, v in req.settings.items()} if req.settings else None
        results = camera_manager.burst_capture(
            count=req.count,
            delay_between=req.delay_between,
            settings=clean_settings
        )
        saved_count = sum(1 for r in results if r.success)
        return {
            "success": saved_count > 0,
            "count": saved_count,
            "requested": req.count,
            "message": f"Fired {saved_count}/{req.count} burst shots directly to camera SD card",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Timelapse / Intervalometer Endpoints
# ==============================================================================

@router.post("/timelapse/start")
def start_timelapse(req: TimelapseStartRequest):
    started = timelapse_engine.start(interval_seconds=req.interval, total_shots=req.count)
    if not started:
        raise HTTPException(status_code=400, detail="Timelapse is already running or could not start.")
    return {"success": True, "status": timelapse_engine.get_status()}


@router.post("/timelapse/stop")
def stop_timelapse():
    stopped = timelapse_engine.stop()
    return {"success": stopped, "status": timelapse_engine.get_status()}


@router.get("/timelapse/status")
def get_timelapse_status():
    return timelapse_engine.get_status()


# ==============================================================================
# System Status Endpoint
# ==============================================================================

@router.get("/system/status")
def get_system_status():
    return {
        "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
        "memory_usage_percent": psutil.virtual_memory().percent,
        "os": f"{platform.system()} {platform.release()}",
        "python_version": sys.version.split()[0],
    }
