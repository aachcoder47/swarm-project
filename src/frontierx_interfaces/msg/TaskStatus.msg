# TaskStatus.msg
# Published by the task executor to report current task state.

std_msgs/Header header

# Unique task ID
string task_id

# Task name (e.g. "find_object", "navigate_to", "patrol")
string task_name

# Human-readable description
string description

# Task state
uint8 IDLE      = 0
uint8 PLANNING  = 1
uint8 EXECUTING = 2
uint8 SUCCEEDED = 3
uint8 FAILED    = 4
uint8 CANCELLED = 5
uint8 state

# Progress [0.0, 1.0]
float32 progress

# Status message (for display)
string status_message

# Error message (if FAILED)
string error_message

# Time task was started
builtin_interfaces/Time started_at

# Estimated completion time (0 if unknown)
builtin_interfaces/Duration estimated_remaining

# Number of sub-steps completed / total
uint32 steps_completed
uint32 steps_total
