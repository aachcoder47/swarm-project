# WorldObject.msg
# A single persistent object in the robot's world model.
# Objects are keyed by object_id and updated on re-detection.

# Unique persistent ID for this world object
string object_id

# Human-readable label (e.g. "red_box", "person_1", "chair")
string label

# Class name from detection pipeline
string class_name

# Position in map frame
geometry_msgs/PoseWithCovariance pose

# 3D dimensions (meters)
geometry_msgs/Vector3 dimensions

# Timestamp of first detection
builtin_interfaces/Time first_seen

# Timestamp of most recent detection
builtin_interfaces/Time last_seen

# Number of times this object has been detected
uint32 observation_count

# Detection confidence (averaged over recent observations)
float32 confidence

# Whether this object is currently visible
bool currently_visible

# Whether this object position is considered stale (not seen in TTL window)
bool is_stale

# Semantic attributes (e.g. {"color": "red", "material": "cardboard"})
string[] attribute_keys
string[] attribute_values

# Object state (e.g. STATIC, DYNAMIC, UNKNOWN)
uint8 STATIC  = 0
uint8 DYNAMIC = 1
uint8 UNKNOWN = 2
uint8 object_state
