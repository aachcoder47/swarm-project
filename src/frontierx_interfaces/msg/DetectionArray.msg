# DetectionArray.msg
# An array of object detections from a single frame.

std_msgs/Header header
frontierx_interfaces/Detection[] detections

# Total number of detections before NMS (for diagnostics)
uint32 raw_detection_count

# Processing time for this frame (milliseconds)
float32 processing_time_ms

# Source sensor frame_id
string sensor_frame
