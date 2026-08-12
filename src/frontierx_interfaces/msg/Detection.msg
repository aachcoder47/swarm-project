# Detection.msg
# A single object detection from the perception pipeline.
#
# Header with timestamp and frame_id (typically camera_link or base_link)
std_msgs/Header header

# Unique detection ID within this frame
uint32 detection_id

# Class label string (e.g. "person", "chair", "red_box")
string class_name

# Numeric class ID (matches YOLO class index)
uint32 class_id

# Detection confidence [0.0, 1.0]
float32 confidence

# 2D bounding box in image coordinates (pixels)
# [x_min, y_min, x_max, y_max]
float32[4] bbox_2d

# 3D centroid position in the frame specified by header.frame_id (meters)
# [0,0,0] if depth is unavailable
geometry_msgs/Point position_3d

# 3D bounding box dimensions (meters)
# width=x, height=y, depth=z
geometry_msgs/Vector3 dimensions_3d

# Whether a valid 3D position was estimated
bool has_3d_pose

# Tracking ID assigned by the tracker (-1 if not tracked)
int32 track_id
