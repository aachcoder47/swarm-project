import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    ros_domain_id = LaunchConfiguration('ros_domain_id', default='0')
    isaac_sim_active = LaunchConfiguration('isaac_sim_active', default='true')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use simulation (Isaac Sim) clock if true'
        ),
        DeclareLaunchArgument(
            'ros_domain_id',
            default_value='0',
            description='ROS 2 DDS Domain ID for Central Brain and Robot Bodies'
        ),
        DeclareLaunchArgument(
            'isaac_sim_active',
            default_value='true',
            description='Enable NVIDIA Isaac Sim ROS 2 Bridge connection'
        ),

        # ── Central AI Brain ROS 2 Bridge Node ──────────────────────────────
        Node(
            package='frontierx_brain',
            executable='brain_node',
            name='central_ai_brain',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'ros_domain_id': ros_domain_id,
                'isaac_sim_active': isaac_sim_active,
            }],
        ),

        # ── Static TF Tree for Multi-Robot Platform ────────────────────────
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='static_tf_map_to_world',
            arguments=['0', '0', '0', '0', '0', '0', 'world', 'map'],
        ),

        # ── Isaac Sim Clock & Telemetry Synchronizer ──────────────────────
        Node(
            package='frontierx_diagnostics',
            executable='safety_monitor_node.py',
            name='safety_monitor',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
        ),
    ])
