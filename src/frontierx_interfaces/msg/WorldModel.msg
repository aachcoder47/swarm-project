# WorldModel.msg
# The complete world model snapshot published by the world model node.

std_msgs/Header header

# All known world objects
frontierx_interfaces/WorldObject[] objects

# Current robot pose estimate in map frame
geometry_msgs/PoseWithCovarianceStamped robot_pose

# Current robot velocity
geometry_msgs/TwistStamped robot_velocity

# Map metadata
string map_frame_id
float32 map_resolution
uint32 map_width
uint32 map_height

# Number of explored / total cells
uint32 explored_cells
uint32 total_cells

# World model session ID (increments on load)
uint32 session_id

# Whether the world model has been loaded from persistent storage
bool loaded_from_disk
