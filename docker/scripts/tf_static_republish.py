#!/usr/bin/env python3
"""Republish /tf_static from TRANSIENT_LOCAL QoS to DEFAULT QoS.

Some Foxglove / ROS 2 tooling does not reliably match TRANSIENT_LOCAL
publishers (used by standard static_transform_publishers) with late-
joining subscribers.  This small bridge captures the latched messages
once using the correct transient-local durability and re-publishes them
with a VOLATILE + reliable profile that every subscriber can pick up,
even if they join well after the original publishers went away.
"""
import threading
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)
from tf2_msgs.msg import TFMessage


SUB_QOS = QoSProfile(
    depth=100,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
)
PUB_QOS = QoSProfile(
    depth=100,
    durability=DurabilityPolicy.VOLATILE,
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
)


def main() -> None:
    rclpy.init()
    node = Node("tf_static_republisher")

    captured: list[TFMessage] = []
    seen_keys: set[tuple[str, str]] = set()
    got_enough = threading.Event()

    def cb(msg: TFMessage) -> None:
        new_keys = set()
        for t in msg.transforms:
            key = (t.header.frame_id, t.child_frame_id)
            new_keys.add(key)
        new_count = sum(1 for k in new_keys if k not in seen_keys)
        if new_count > 0:
            captured.append(msg)
            seen_keys.update(new_keys)
            node.get_logger().info(
                f"captured {len(seen_keys)} unique static frames"
            )
        if len(seen_keys) >= 12:
            got_enough.set()

    _sub = node.create_subscription(TFMessage, "/tf_static", cb, SUB_QOS)
    pub = node.create_publisher(TFMessage, "/tf_static", PUB_QOS)

    start = time.time()
    while not got_enough.is_set() and (time.time() - start) < 8.0:
        rclpy.spin_once(node, timeout_sec=0.1)

    if not captured:
        node.get_logger().warn("no /tf_static messages captured; continuing loop")
    else:
        node.get_logger().info(
            f"republishing {len(captured)} static-TF batches"
        )

    deadline = time.time() + 12.0
    while time.time() < deadline:
        for msg in captured:
            pub.publish(msg)
        time.sleep(0.5)

    node.get_logger().info("tf_static republisher done")
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
