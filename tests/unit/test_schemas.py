"""
FrontierX Unit Tests — T01 Schemas & Canonical Registry
======================================================
"""

from __future__ import annotations

import pytest
from frontierx_brain.core.schemas import (
    SkillType,
    Capability,
    CANONICAL_SKILL_DEFINITIONS,
    ALLOWED_ACTION_WHITELIST,
)


def test_t01_canonical_schemas() -> None:
    """T01 Schemas: Verify canonical skill definitions and allowed action whitelists match."""
    assert len(CANONICAL_SKILL_DEFINITIONS) == 13
    # Each defines req_caps, body_types, timeout, retries
    for s in CANONICAL_SKILL_DEFINITIONS:
        assert isinstance(s.skill_id, SkillType)
        assert s.default_timeout_seconds >= 1.0
        assert s.max_retries >= 0
        # navigate_to → navigate_ground required
        if s.skill_id == SkillType.NAVIGATE_TO:
            assert Capability.NAVIGATE_GROUND in s.required_capabilities
        if s.skill_id == SkillType.ARM_PICK:
            assert Capability.MANIPULATE_ARM in s.required_capabilities
            assert Capability.GRASP in s.required_capabilities
        if s.skill_id == SkillType.INSPECT:
            assert Capability.CAPTURE_RGB in s.required_capabilities
    # Whitelist matches canonical skill enums exactly (no drift)
    assert set(ALLOWED_ACTION_WHITELIST) == set(s.value for s in SkillType)
