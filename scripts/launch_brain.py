#!/usr/bin/env python3
"""
Master Central AI Brain Launcher Script (ROS 2 & Isaac Sim Native)
===================================================================
Launches the FrontierX Central AI Brain Server, FastAPI API Gateway,
Multi-Robot Orchestrator, ROS 2 DDS Bridge, and NVIDIA Isaac Sim connector.

Usage:
  python scripts/launch_brain.py --port 8000 --ros2 --isaac-sim
"""

import argparse
import os
import sys
import time

# Ensure src directory is in PYTHONPATH
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src", "frontierx_brain"))

from frontierx_brain.api.gateway import CentralBrainSystem, create_app, FASTAPI_AVAILABLE
from frontierx_brain.observability.observability import brain_logger


def main() -> None:
    parser = argparse.ArgumentParser(description="FrontierX Central AI Brain Launcher")
    parser.add_argument("--host", default="127.0.0.1", help="Host address to bind server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run FastAPI server")
    parser.add_argument("--ros2", action="store_true", help="Enable ROS 2 DDS node bridge")
    parser.add_argument("--isaac-sim", action="store_true", help="Connect to NVIDIA Isaac Sim ROS 2 bridge")
    args = parser.parse_args()

    print("===============================================================")
    print("      FRONTIERX CENTRAL AI BRAIN PLATFORM (ROS 2 & ISAAC SIM)  ")
    print("===============================================================")

    brain_system = CentralBrainSystem()
    brain_logger.info(f"Initialized Central AI Brain. Mode: ROS 2={args.ros2}, IsaacSim={args.isaac_sim}")

    if FASTAPI_AVAILABLE:
        try:
            import uvicorn
            print(f"🚀 Launching FastAPI Gateway on http://{args.host}:{args.port}")
            print(f"📊 Web Application Dashboard available at: dashboard/index.html")
            app = create_app()
            uvicorn.run(app, host=args.host, port=args.port)
        except ImportError:
            print("Notice: uvicorn not installed. Running background brain event loop...")
            run_standalone_loop(brain_system)
    else:
        print("Notice: FastAPI not installed. Running standalone brain event loop...")
        run_standalone_loop(brain_system)


def run_standalone_loop(brain_system: CentralBrainSystem) -> None:
    """Run pure Python event loop if uvicorn/fastapi is not installed."""
    brain_logger.info("Standalone event loop running. Press Ctrl+C to exit.")
    try:
        while True:
            brain_system.state_monitor.check_health_watchdogs()
            brain_system.teleop.check_deadman_timeout()
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nShutdown signal received. Stopping Central AI Brain...")


if __name__ == "__main__":
    main()
