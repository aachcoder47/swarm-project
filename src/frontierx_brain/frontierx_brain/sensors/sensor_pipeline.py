"""
Component 12: Sensor Data Pipeline
==================================
Subscribes to and aggregates multi-robot sensor streams (RGB camera, LiDAR point clouds,
thermal camera feeds, IMU), handles frame compression, and streams to WebSocket dashboard clients.
"""

from __future__ import annotations

import base64
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CameraFrame(BaseModel):
    robot_id: str
    camera_type: str = "RGB"  # RGB, DEPTH, THERMAL
    width: int = 640
    height: int = 480
    encoding: str = "jpeg"
    base64_data: str = ""
    timestamp: float = Field(default_factory=time.time)


class SensorDataPipeline:
    """Central sensor stream aggregator and compressor."""

    def __init__(self) -> None:
        self._latest_frames: Dict[str, CameraFrame] = {}

    def ingest_frame(self, frame: CameraFrame) -> None:
        key = f"{frame.robot_id}_{frame.camera_type}"
        self._latest_frames[key] = frame

    def get_latest_frame(self, robot_id: str, camera_type: str = "RGB") -> Optional[CameraFrame]:
        key = f"{robot_id}_{camera_type}"
        return self._latest_frames.get(key)

    def list_active_streams(self) -> List[str]:
        return list(self._latest_frames.keys())
