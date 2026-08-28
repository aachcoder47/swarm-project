"""
FrontierX Unit Tests — T09 World Model Queries
==============================================
"""

from __future__ import annotations

import pytest
from frontierx_brain.world.world_model import WorldModel, WorldObject


def test_t09_world_model_query() -> None:
    """T09: WorldModel query_world returns objects matching criteria."""
    wm = WorldModel()
    wm.upsert_object(WorldObject(object_id="a", class_name="generator", x=1, y=2, status="UNINSPECTED"))
    wm.upsert_object(WorldObject(object_id="b", class_name="valve", x=0, y=0, status="OK"))
    matches = wm.find_objects(class_name="generator")
    assert len(matches) == 1 and matches[0].object_id == "a"
