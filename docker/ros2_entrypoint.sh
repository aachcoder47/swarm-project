#!/bin/bash
# ros2_entrypoint.sh — ROS 2 Docker entrypoint
set -e

# Source ROS 2
source /opt/ros/humble/setup.bash

# Source workspace if built
if [ -f /opt/ros_ws/install/setup.bash ]; then
  source /opt/ros_ws/install/setup.bash
fi

exec "$@"
