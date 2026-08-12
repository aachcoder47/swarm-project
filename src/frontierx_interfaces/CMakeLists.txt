cmake_minimum_required(VERSION 3.8)
project(frontierx_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(action_msgs REQUIRED)

# ── Messages ──────────────────────────────────────────────────
set(MSG_FILES
  "msg/Detection.msg"
  "msg/DetectionArray.msg"
  "msg/WorldObject.msg"
  "msg/WorldModel.msg"
  "msg/RobotHealth.msg"
  "msg/TaskStatus.msg"
)

# ── Services ──────────────────────────────────────────────────
set(SRV_FILES
  "srv/QueryWorldModel.srv"
  "srv/ExecuteTask.srv"
  "srv/SetNavigationMode.srv"
  "srv/ResetRobot.srv"
)

# ── Actions ───────────────────────────────────────────────────
set(ACTION_FILES
  "action/NavigateToGoal.action"
  "action/FindObject.action"
  "action/FollowPerson.action"
  "action/ExecuteTaskPlan.action"
  "action/Dock.action"
)

rosidl_generate_interfaces(${PROJECT_NAME}
  ${MSG_FILES}
  ${SRV_FILES}
  ${ACTION_FILES}
  DEPENDENCIES
    std_msgs
    geometry_msgs
    sensor_msgs
    nav_msgs
    builtin_interfaces
    action_msgs
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
