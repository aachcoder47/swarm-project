# FrontierX Scout — Testing & Benchmarking

> **Document:** 11 — Testing & Benchmarking  
> **Version:** 0.1.0

---

## 1. Test Strategy

1. **Unit Tests:** `pytest` for Python nodes, `GoogleTest` for C++ interfaces.
2. **Interface Validation:** CI checks `frontierx_interfaces` compilation.
3. **URDF Integrity:** `check_urdf` verifies Xacro output.
4. **Automated Benchmarks:** `frontierx_data` logs navigation success rate, path efficiency, localization error, and perception mAP.
