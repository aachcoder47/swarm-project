import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


from launch_ros.actions import Node


def generate_launch_description():
    nav2_share = get_package_share_directory('nav2_bringup')
    nav2_launch_path = os.path.join(nav2_share, 'launch', 'navigation_launch.py')

    return LaunchDescription([
        # Static TF broadcast directly inside navigation stack
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='nav_tf_map_to_odom',
            arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='nav_tf_odom_to_base_footprint',
            arguments=['0', '0', '0', '0', '0', '0', 'odom', 'base_footprint'],
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='nav_tf_base_footprint_to_base_link',
            arguments=['0', '0', '0.1', '0', '0', '0', 'base_footprint', 'base_link'],
        ),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_launch_path),
            launch_arguments={
                'use_sim_time': 'false',
                'autostart': 'true',
            }.items(),
        ),
    ])
