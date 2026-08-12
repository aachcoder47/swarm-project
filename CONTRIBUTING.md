# Contributing to FrontierX Robotics

Thank you for your interest in contributing to FrontierX Scout — the open autonomous robotics platform by FrontierX Labs.

---

## Code of Conduct

Be professional, respectful, and technically rigorous. We prioritize quality over quantity.

---

## How to Contribute

### 1. Fork and Clone

```bash
git clone https://github.com/frontierx-labs/frontierx-robotics.git
cd frontierx-robotics
```

### 2. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

### 3. Make Changes

Follow the coding standards below.

### 4. Test

```bash
./scripts/build.sh
./scripts/run_tests.sh
```

### 5. Commit

Use conventional commits:

```
feat(perception): add YOLOv8 TensorRT export support
fix(navigation): correct costmap inflation radius
docs(slam): update SLAM Toolbox configuration guide
test(localization): add EKF drift benchmark
refactor(agent): split task validator into separate module
```

### 6. Pull Request

- Describe the change clearly
- Link any related issues
- Include benchmark results if performance-relevant
- Attach a demo video/screenshot for UI/visualization changes

---

## Coding Standards

### Python

- **Formatter:** `black` (line length 100)
- **Linter:** `flake8` + `ament_flake8`
- **Type hints:** Required for all public functions
- **Docstrings:** Google-style

```python
def navigate_to(x: float, y: float, theta: float = 0.0) -> bool:
    """Navigate the robot to a goal pose.

    Args:
        x: Goal x position in map frame (meters).
        y: Goal y position in map frame (meters).
        theta: Goal heading in radians. Defaults to 0.0.

    Returns:
        True if navigation succeeded, False otherwise.
    """
```

### C++

- **Standard:** C++17
- **Formatter:** `clang-format` (Google style)
- **Linter:** `ament_clang-format`, `ament_cppcheck`
- **Naming:** `snake_case` for variables/functions, `CamelCase` for classes

### ROS 2

- Always use `rclcpp::Logger` / `rclpy.logging` — never `std::cout` or `print()`
- Use ROS 2 parameters for all configuration — never hard-code values
- Use QoS profiles appropriate to the data type
- Always handle publisher/subscriber lifecycle correctly
- Use actions for long-running operations, services for queries

### URDF/Xacro

- All links must have `<inertial>` elements with realistic values
- All links must have `<collision>` and `<visual>` elements
- Frame names must match the TF tree specification in [02-robot-description.md](docs/02-robot-description.md)

---

## Testing Requirements

All contributions must include:

- **Unit tests** for new Python modules (`pytest`)
- **Integration tests** for new ROS 2 nodes (`ros2 launch ... test:=true`)
- **Updated benchmarks** if performance-relevant

Test files go in:
- `src/<package>/test/` (package-level)
- `tests/` (integration)

---

## Documentation Requirements

- New packages require a `README.md`
- New nodes require parameter documentation
- New topics/services/actions must be added to [03-ros2-architecture.md](docs/03-ros2-architecture.md)
- Significant features require updating the relevant architecture document

---

## Safety-Critical Code

Any code that affects robot motion, safety systems, or the agent's action validation layer requires:

1. Extra review from at least one maintainer
2. Formal description of the safety properties being maintained
3. Test cases that verify the safety constraint holds

**The golden rule:** The LLM agent must NEVER be able to directly control actuators. All motion commands must pass through the deterministic safety layer.

---

## Repository Structure Rules

```
src/<package>/          # All ROS 2 packages go here
config/                 # YAML configuration (never hard-code)
docs/                   # Architecture documentation
docker/                 # Container configuration
scripts/                # Development utilities
tests/                  # Integration tests
```

Do NOT commit:
- Build artifacts (`build/`, `install/`, `log/`)
- ROS bags (`.db3`, `.mcap`)
- Model weights (`.pt`, `.engine`) — use model registry
- Secrets or API keys
- Isaac Sim cache files

---

## Issue Labels

| Label | Meaning |
|-------|---------|
| `phase-N` | Belongs to development phase N |
| `bug` | Something is broken |
| `enhancement` | New feature or improvement |
| `safety` | Safety-critical — extra review required |
| `benchmark` | Performance measurement |
| `docs` | Documentation improvement |
| `sim-only` | Simulation environment |
| `real-robot` | Physical hardware |

---

*FrontierX Labs — Build the machines of tomorrow.*
