cmake_minimum_required(VERSION 3.8)
project(frontierx_robot_description)

find_package(ament_cmake REQUIRED)

# Install all URDF/Xacro, config, launch, and rviz files
install(DIRECTORY
  urdf
  meshes
  config
  launch
  rviz
  DESTINATION share/${PROJECT_NAME}/
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
