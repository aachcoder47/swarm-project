"""
FrontierX Gazebo Sim Launch File
==================================
Launches Gazebo Harmonic (gz sim) with:
  - frontierx_warehouse.sdf world
  - Scout robot (URDF via robot_state_publisher)
  - ros_gz_bridge for topic bridging
  - RViz2 for visualization

Usage:
  ros2 launch frontierx_sim gazebo.launch.py
  ros2 launch frontierx_sim gazebo.launch.py world:=frontierx_warehouse headless:=true
"""

import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    ExecuteProcess,
    RegisterEventHandler,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    PythonExpression,
)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # ── Package paths ────────────────────────────────────────
    pkg_sim      = get_package_share_directory("frontierx_sim")
    pkg_desc     = get_package_share_directory("frontierx_robot_description")

    # ── Launch arguments ─────────────────────────────────────
    world_arg = DeclareLaunchArgument(
        "world",
        default_value="frontierx_warehouse",
        description="Gazebo world name (without .sdf extension)",
    )
    headless_arg = DeclareLaunchArgument(
        "headless",
        default_value="false",
        description="Run Gazebo without GUI (server only)",
    )
    use_sim_time_arg = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use Gazebo simulation clock",
    )
    robot_x_arg = DeclareLaunchArgument("robot_x", default_value="0.0")
    robot_y_arg = DeclareLaunchArgument("robot_y", default_value="0.0")
    robot_z_arg = DeclareLaunchArgument("robot_z", default_value="0.05")
    robot_yaw_arg = DeclareLaunchArgument("robot_yaw", default_value="0.0")

    world          = LaunchConfiguration("world")
    headless       = LaunchConfiguration("headless")
    use_sim_time   = LaunchConfiguration("use_sim_time")
    robot_x        = LaunchConfiguration("robot_x")
    robot_y        = LaunchConfiguration("robot_y")
    robot_z        = LaunchConfiguration("robot_z")
    robot_yaw      = LaunchConfiguration("robot_yaw")

    # ── URDF / Xacro ─────────────────────────────────────────
    urdf_xacro = os.path.join(pkg_desc, "urdf", "scout.urdf.xacro")
    urdf_processed = xacro.process_file(urdf_xacro).toxml()

    # ── GZ_SIM_RESOURCE_PATH so gz sim can find our worlds ───
    set_gz_resource = SetEnvironmentVariable(
        name="GZ_SIM_RESOURCE_PATH",
        value=os.path.join(pkg_sim, "worlds") + ":" +
              os.path.join(pkg_sim, "models"),
    )

    # ── 1. Gazebo Sim (gz sim) ───────────────────────────────
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare("ros_gz_sim"),
                "launch",
                "gz_sim.launch.py",
            ])
        ]),
        launch_arguments={
            "gz_args": PythonExpression([
                '"-r -v4 " + "',
                os.path.join(pkg_sim, "worlds"),
                '/" + "',
                world,
                '" + ".sdf" + (" -s" if "',
                headless,
                '" == "true" else "")',
            ]),
            "on_exit_shutdown": "true",
        }.items(),
    )

    # ── 2. Robot State Publisher ─────────────────────────────
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "robot_description": urdf_processed,
        }],
    )

    # ── 3. Spawn robot into Gazebo ───────────────────────────
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_frontierx_scout",
        output="screen",
        arguments=[
            "-name",   "frontierx_scout",
            "-string", urdf_processed,
            "-x",      robot_x,
            "-y",      robot_y,
            "-z",      robot_z,
            "-Y",      robot_yaw,
        ],
    )

    # ── 4. ros_gz_bridge — topic type mapping ────────────────
    #    Bridges Gazebo ↔ ROS 2 topics for the Scout robot.
    gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_ros2_bridge",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "config_file": os.path.join(pkg_sim, "config", "gz_bridge.yaml"),
        }],
    )

    # ── 5. Joint State Bridge ────────────────────────────────
    gz_joint_state_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_joint_state_bridge",
        output="screen",
        arguments=[
            "/world/frontierx_warehouse/model/frontierx_scout/joint_state"
            "@sensor_msgs/msg/JointState[gz.msgs.Model",
        ],
        remappings=[
            (
                "/world/frontierx_warehouse/model/frontierx_scout/joint_state",
                "/joint_states",
            )
        ],
    )

    # ── 6. RViz2 ─────────────────────────────────────────────
    rviz_config = os.path.join(pkg_desc, "rviz", "frontierx_scout.rviz")
    rviz = Node(
        condition=UnlessCondition(headless),
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        output="screen",
        arguments=["-d", rviz_config] if os.path.exists(rviz_config) else [],
        parameters=[{"use_sim_time": use_sim_time}],
    )

    return LaunchDescription([
        # Env
        set_gz_resource,
        # Args
        world_arg,
        headless_arg,
        use_sim_time_arg,
        robot_x_arg,
        robot_y_arg,
        robot_z_arg,
        robot_yaw_arg,
        # Nodes
        gz_sim,
        robot_state_publisher,
        spawn_robot,
        gz_bridge,
        gz_joint_state_bridge,
        rviz,
    ])
