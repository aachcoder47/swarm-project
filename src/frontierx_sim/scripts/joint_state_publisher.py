#!/usr/bin/env python3
"""
Simple joint state publisher for Gazebo Sim compatibility.
Publishes static joint states for robot visualization in RViz2.
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class SimpleJointStatePublisher(Node):
    def __init__(self):
        super().__init__('simple_joint_state_publisher')
        
        self.publisher = self.create_publisher(JointState, '/joint_states', 10)
        self.timer = self.create_timer(0.1, self.publish_joint_states)
        
        # Define joint names for the Scout robot
        self.joint_names = [
            'wheel_left_link_joint',
            'wheel_right_link_joint',
            'caster_front_link_joint',
            'caster_rear_link_joint',
            'sensor_mast_joint',
            'laser_frame_joint',
            'camera_joint',
            'camera_optical_joint',
            'camera_depth_joint',
            'camera_depth_optical_joint',
            'imu_joint',
        ]
        
        self.get_logger().info('Simple Joint State Publisher started')

    def publish_joint_states(self):
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = self.joint_names
        msg.position = [0.0] * len(self.joint_names)
        msg.velocity = [0.0] * len(self.joint_names)
        msg.effort = [0.0] * len(self.joint_names)
        
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SimpleJointStatePublisher()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
