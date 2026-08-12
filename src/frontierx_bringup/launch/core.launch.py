import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
import xacro


def generate_launch_description():
    # ── Robot Description (URDF via Xacro) ──────────────────────
    desc_pkg = get_package_share_directory('frontierx_robot_description')
    xacro_path = os.path.join(desc_pkg, 'urdf', 'scout.urdf.xacro')
    robot_description_config = xacro.process_file(xacro_path).toxml()

    return LaunchDescription([
        # ── Robot State Publisher ────────────────────────────────
        # Publishes /tf, /tf_static, and /robot_description
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'robot_description': robot_description_config,
                'use_sim_time': False,
            }],
        ),

        # ── Continuous TF Broadcaster (map -> odom -> base_footprint -> base_link) ───
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='tf_map_to_odom',
            arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='tf_odom_to_base_footprint',
            arguments=['0', '0', '0', '0', '0', '0', 'odom', 'base_footprint'],
        ),
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            name='tf_base_footprint_to_base_link',
            arguments=['0', '0', '0.1', '0', '0', '0', 'base_footprint', 'base_link'],
        ),

        # ── Visual Marker Publisher (robot body, red box, /map) ──
        Node(
            package='frontierx_visualization',
            executable='marker_publisher_node.py',
            name='marker_publisher',
            output='screen',
        ),
    ])
