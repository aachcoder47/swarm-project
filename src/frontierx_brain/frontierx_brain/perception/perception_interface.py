"""
Component 13: Perception Interface
==================================
Interfaces object detection pipelines (YOLOv8, VLM zero-shot, thermal analytics)
with the Central World Model. Updates object poses, bounding boxes, and detection confidence.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from frontierx_brain.world.world_model import WorldModel, WorldObject
from frontierx_brain.observability.observability import brain_logger


class PerceptionInterface:
    """Processes perception inputs and maintains live world object states."""

    def __init__(self, world_model: WorldModel) -> None:
        self.world_model = world_model

    def process_detection(
        self,
        robot_id: str,
        class_name: str,
        confidence: float,
        x: float,
        y: float,
        z: float = 0.0,
        object_id: Optional[str] = None,
        status: str = "NORMAL",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorldObject:
        """Ingest single perception object detection and update World Model."""
        obj_id = object_id or f"{class_name.lower()}_{int(x*10)}_{int(y*10)}"
        existing = self.world_model.get_object(obj_id)

        if existing:
            existing.confidence = max(existing.confidence, confidence)
            existing.x = x
            existing.y = y
            existing.z = z
            existing.status = status
            existing.detected_by_robot = robot_id
            existing.last_seen = time.time()
            if metadata:
                existing.metadata.update(metadata)
            updated_obj = self.world_model.upsert_object(existing)
        else:
            new_obj = WorldObject(
                object_id=obj_id,
                class_name=class_name,
                confidence=confidence,
                x=x,
                y=y,
                z=z,
                status=status,
                detected_by_robot=robot_id,
                metadata=metadata or {},
            )
            updated_obj = self.world_model.upsert_object(new_obj)
            brain_logger.info(
                f"Perception detected new object '{obj_id}' ({class_name}) at ({x:.1f}, {y:.1f}) by Robot {robot_id}.",
                robot_id=robot_id,
            )

        return updated_obj
