# FrontierX Scout — Perception Pipeline

> **Document:** 05 — Perception Pipeline  
> **Version:** 0.1.0  
> **Target:** 3D Real-Time Semantic Spatial Understanding

---

## 1. Overview

The `frontierx_perception` package processes visual and spatial sensor streams to deliver 3D semantically annotated object tracks to the world model. Rather than providing 2D bounding boxes in image space, the perception pipeline computes real-world 3D coordinates ($x, y, z$) in the `map` frame for every detected object.

---

## 2. Perception Architecture

```
┌───────────────────────────┐     ┌───────────────────────────┐
│   /camera/image_raw       │     │  /camera/depth/image_raw  │
│   (1280x720 RGB Frame)    │     │  (640x480 Depth Map)      │
└─────────────┬─────────────┘     └─────────────┬─────────────┘
              │                                 │
┌─────────────▼─────────────┐                   │
│   YOLOv8 Object Detector  │                   │
│   (PyTorch / TensorRT)    │                   │
└─────────────┬─────────────┘                   │
              │ 2D BBoxes                       │
┌─────────────▼─────────────┐                   │
│   ByteTrack MOT Engine    │                   │
│   (Persistent Track IDs)  │                   │
└─────────────┬─────────────┘                   │
              │ 2D BBoxes + IDs                 │
┌─────────────▼─────────────────────────────────▼─────────────┐
│                 3D Spatial Localizer                        │
│   - Depth Sampling at BBox Centroid                         │
│   - Pin-hole Camera De-projection to 3D Camera Frame       │
│   - TF Transform (camera_optical_frame → map frame)        │
└─────────────┬───────────────────────────────────────────────┘
              │
┌─────────────▼───────────────────────────────────────────────┐
│     /perception/tracks (frontierx_interfaces/DetectionArray) │
│     3D Positions + Track IDs + Class Labels                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Component Details

### 3.1 Object Detection (YOLOv8)
- **Model Size:** YOLOv8m (Medium) optimized for real-time inference on NVIDIA GPUs
- **Inference Engine:** PyTorch in simulation; TensorRT FP16 engine on physical Jetson hardware
- **Classes Tracked:** Furniture (chairs, tables, couches), obstacles (boxes, barrels), humans, doors, charging stations
- **Target Performance:** $\ge 20\text{ FPS}$ @ 720p, $\text{mAP@50} \ge 80\%$

### 3.2 Multi-Object Tracking (ByteTrack)
- Maintains identity persistence across temporary occlusions (up to 30 frames)
- Employs Kalman filtering on bounding box velocities to match low-confidence detections

### 3.3 3D Spatial Localization
- Given 2D pixel coordinates $(u, v)$ and depth value $Z$ from depth map:
  $$X = \frac{(u - c_x) \times Z}{f_x}, \quad Y = \frac{(v - c_y) \times Z}{f_y}$$
- Using static TF transforms, $(X, Y, Z)_{\text{camera}}$ is transformed into $(X, Y, Z)_{\text{map}}$
