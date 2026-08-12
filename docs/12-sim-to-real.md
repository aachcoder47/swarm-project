# FrontierX Scout — Sim-to-Real Deployment

> **Document:** 12 — Sim-to-Real Deployment  
> **Version:** 0.1.0

---

## 1. Physical Hardware Roadmap

Once the complete simulation MVP is validated in Isaac Sim:
- **Compute:** NVIDIA Jetson Orin Nano
- **Microcontroller:** Teensy 4.1 / STM32 for low-level motor PID loop
- **Sensors:** RPLIDAR A1M8/A2M8 + Intel RealSense D435i + MPU6050
- **Actuators:** 12V DC Encoder Gear Motors + L298N/MDD10A Drivers

The software stack requires **zero changes** to autonomy packages; only hardware ROS 2 bridge nodes are substituted.
