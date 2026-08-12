import os
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='frontierx_perception',
            executable='perception_node.py',
            name='perception_node',
            output='screen',
        )
    ])
