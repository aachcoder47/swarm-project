# RobotHealth.msg
# System health and diagnostic summary published by the safety monitor.

std_msgs/Header header

# Overall system health
uint8 NOMINAL   = 0
uint8 DEGRADED  = 1
uint8 E_STOP    = 2
uint8 RECOVERY  = 3
uint8 FAULT     = 4
uint8 system_state

# Individual subsystem health flags
bool lidar_ok
bool camera_rgb_ok
bool camera_depth_ok
bool imu_ok
bool odometry_ok
bool navigation_ok
bool perception_ok
bool world_model_ok
bool agent_ok

# Sensor timestamps (for staleness detection)
builtin_interfaces/Time lidar_last_stamp
builtin_interfaces/Time camera_last_stamp
builtin_interfaces/Time imu_last_stamp
builtin_interfaces/Time odom_last_stamp

# Velocity limits being applied
float32 v_max_current
float32 omega_max_current

# E-stop state
bool e_stop_active
string e_stop_reason

# Active fault descriptions
string[] active_faults

# System uptime (seconds)
float64 uptime_seconds

# Resource usage
float32 cpu_percent
float32 memory_percent
float32 gpu_percent
