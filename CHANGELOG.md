# Changelog

All notable changes to FrontierX are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Enterprise security hardening: non-root Docker user (`frontierx` UID=1000)
- Docker `security_opt: no-new-privileges`, `cap_drop: ALL`, resource limits
- Docker healthchecks on all services
- Structured JSON log rotation (`max-size: 100m, max-file: 5`)
- GitHub Actions security workflow: Trivy, Bandit, pip-audit, Trufflehog
- GitHub Actions release workflow: multi-platform GHCR publish + cosign signing
- Prometheus metrics exporter (`frontierx_brain/observability/metrics.py`)
- Structured JSON logger (`frontierx_brain/observability/logger.py`)
- Prometheus + Grafana monitoring profile in docker-compose
- `pyproject.toml` unified tooling config (ruff, mypy, black, isort, pytest)
- `.pre-commit-config.yaml` with black, ruff, mypy, hadolint, detect-secrets
- `scripts/deploy.sh` — one-command environment-aware deploy
- `scripts/healthcheck.sh` — post-deploy service verification
- OCI image labels for build traceability
- `CHANGELOG.md`

---

## [1.0.0] — 2026-08-01

### Added
- Initial FrontierX robotics platform scaffold
- ROS 2 Humble Docker stack with Nav2, SLAM Toolbox, EKF
- FrontierX Scout URDF with sensors (LiDAR, RGB, Depth, IMU)
- `frontierx_brain` — Central AI brain with 17 sub-modules
- `frontierx_interfaces` — Custom ROS 2 messages, services, actions
- 18-test suite with benchmarks (`tests/test_brain_system.py`)
- GitHub Actions CI: lint, build, validate-interfaces, validate-URDF, unit tests
- Docker Compose multi-service orchestration (build, core, navigation, perception, agent, safety, foxglove, dashboard)
- Foxglove Studio WebSocket bridge for visualization
- Ollama LLM server integration (LLaMA 3.1)
- Web dashboard (nginx)
- ROADMAP.md with 12-month development phases

[Unreleased]: https://github.com/frontierx-labs/frontierx-robotics/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/frontierx-labs/frontierx-robotics/releases/tag/v1.0.0
