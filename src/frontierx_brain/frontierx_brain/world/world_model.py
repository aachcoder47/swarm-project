"""
Component 6: Central World Model (Production Mode — No Mock Data)
==================================================================
Central spatial and semantic entity database for all connected robot bodies.
Stores objects, locations, rooms, zones, dynamic obstacles, 3D poses, bounding boxes.
Starts empty and populates exclusively via real ROS 2 perception streams and API calls.
"""

from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class WorldObject(BaseModel):
    object_id: str
    class_name: str
    confidence: float = 1.0
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    bbox_size: List[float] = Field(default_factory=lambda: [0.5, 0.5, 0.5])
    status: str = "NORMAL"  # e.g., NORMAL, ABNORMAL, INSPECTED, FAULT
    detected_by_robot: Optional[str] = None
    last_seen: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorldModel:
    """Production spatial & semantic world database (Starts clean, no pre-seeded mock data)."""

    def __init__(self) -> None:
        self._objects: Dict[str, WorldObject] = {}

    def upsert_object(self, obj: WorldObject) -> WorldObject:
        """Insert or update a real world object entity."""
        obj.last_seen = time.time()
        self._objects[obj.object_id] = obj
        return obj

    def remove_object(self, object_id: str) -> bool:
        if object_id in self._objects:
            del self._objects[object_id]
            return True
        return False

    def get_object(self, object_id: str) -> Optional[WorldObject]:
        return self._objects.get(object_id)

    def find_objects(
        self,
        class_name: Optional[str] = None,
        status: Optional[str] = None,
        query: Optional[str] = None,
    ) -> List[WorldObject]:
        results = list(self._objects.values())
        if class_name:
            results = [o for o in results if o.class_name.lower() == class_name.lower()]
        if status:
            results = [o for o in results if o.status.lower() == status.lower()]
        if query:
            q = query.lower()
            results = [
                o for o in results
                if q in o.object_id.lower() or q in o.class_name.lower() or q in str(o.metadata).lower()
            ]
        return results

    def query_nearest_object(self, x: float, y: float, class_name: Optional[str] = None) -> Optional[WorldObject]:
        candidates = self.find_objects(class_name=class_name)
        if not candidates:
            return None

        best_obj = None
        min_dist = float("inf")
        for obj in candidates:
            dist = math.sqrt((obj.x - x) ** 2 + (obj.y - y) ** 2)
            if dist < min_dist:
                min_dist = dist
                best_obj = obj
        return best_obj

    def get_all_objects(self) -> List[WorldObject]:
        return list(self._objects.values())
