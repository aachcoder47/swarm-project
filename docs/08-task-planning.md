# FrontierX Scout — Task Planning & World Model

> **Document:** 08 — Task Planning & World Model  
> **Version:** 0.1.0

---

## 1. Overview

High-level autonomy requires structured representations of the environment beyond occupancy grids. The `frontierx_tasks` package provides:
1. **World Model Node:** Tracks persistent 3D objects (chairs, boxes, humans) with spatial attributes and freshness timestamps.
2. **Task Executor Action Server:** Translates high-level goals (`find_object`, `patrol`, `dock`) into sequences of Nav2 goals and perception checks.
