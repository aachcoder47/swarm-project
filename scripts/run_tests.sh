#!/usr/bin/env bash
# =============================================================
# FrontierX Scout — Run Tests
# =============================================================
set -euo pipefail

FRONTIERX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${FRONTIERX_ROOT}"

source /opt/ros/humble/setup.bash
source install/setup.bash

echo "Running FrontierX test suite..."
colcon test \
  --event-handlers \
    console_cohesion+ \
  --return-code-on-test-failure

colcon test-result --verbose
echo "Tests complete."
