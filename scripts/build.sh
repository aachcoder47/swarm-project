#!/usr/bin/env bash
# =============================================================
# FrontierX Scout — Build Script
# =============================================================
set -euo pipefail

FRONTIERX_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${FRONTIERX_ROOT}"

echo "Building FrontierX workspace..."
source /opt/ros/humble/setup.bash

colcon build \
  --symlink-install \
  --cmake-args \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
  --event-handlers \
    console_cohesion+ \
    summary+

source install/setup.bash
echo "Build complete. Workspace ready."
