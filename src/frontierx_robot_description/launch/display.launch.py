#!/usr/bin/env python3
"""
FrontierX Scout — display.launch.py
Launch robot_state_publisher + joint_state_publisher_gui + RViz2
for URDF inspection on the desktop (no simulation required).

Usage:
  ros2 launch frontierx_robot_description display.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    pkg = get_package_share_directory('frontierx_robot_description')

    urdf_file = os.path.join(pkg, 'urdf', 'scout.urdf.xacro')
    rviz_config = os.path.join(pkg, 'rviz', 'urdf_preview.rviz')

    # Process Xacro
    robot_description = xacro.process_file(urdf_file).toxml()

    use_gui_arg = DeclareLaunchArgument(
        'use_gui',
        default_value='true',
        description='Whether to start joint_state_publisher_gui',
    )
    use_gui = LaunchConfiguration('use_gui')

    return LaunchDescription([
        use_gui_arg,

        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': False,
            }],
        ),

        Node(
            package='joint_state_publisher_gui',
            executable='joint_state_publisher_gui',
            name='joint_state_publisher_gui',
            output='screen',
            condition=IfCondition(use_gui),
        ),

        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
        ),
    ])
