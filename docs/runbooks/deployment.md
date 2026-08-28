# FrontierX Deployment Runbook

> **Audience:** DevOps / Platform engineers
> **Last updated:** 2026-08-29

---

## Prerequisites

| Tool | Minimum Version |
|------|----------------|
| Docker | 24.0+ |
| Docker Compose | v2.20+ |
| Git | 2.40+ |
| bash | 5.0+ (Linux/macOS/WSL2) |

---

## Environment Variables

Copy and fill in before deploying:

```bash
cp docker/.env.example docker/.env
# Required:
ROS_DOMAIN_ID=42
# Optional — production:
GRAFANA_USER=admin
GRAFANA_PASSWORD=<strong-password>
LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://ollama:11434
```

---

## Quick Deploy

```bash
# Development
./scripts/deploy.sh dev

# Production
export ROS_DOMAIN_ID=42
export GRAFANA_PASSWORD=<secret>
./scripts/deploy.sh prod
```

---

## Manual Step-by-Step

### 1. Build the Docker image

```bash
export BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
export VERSION=$(git describe --tags --always)
export REVISION=$(git rev-parse --short HEAD)

docker compose -f docker/docker-compose.yml build \
  --build-arg BUILD_DATE=$BUILD_DATE \
  --build-arg VERSION=$VERSION \
  --build-arg REVISION=$REVISION
```

### 2. Start the core stack

```bash
docker compose -f docker/docker-compose.yml up -d
```

### 3. Start with monitoring

```bash
docker compose -f docker/docker-compose.yml \
  --profile monitoring up -d
```

### 4. Verify health

```bash
./scripts/healthcheck.sh
```

### 5. View logs

```bash
# All services
docker compose -f docker/docker-compose.yml logs -f

# Single service
docker logs frontierx_ros2_core -f --tail 100
```

---

## Rollback Procedure

```bash
# Stop current deployment
docker compose -f docker/docker-compose.yml down

# Pull previous image tag
docker pull ghcr.io/frontierx-labs/ros2-humble:<previous-version>
docker tag ghcr.io/frontierx-labs/ros2-humble:<prev> frontierx/ros2-humble:latest

# Restart
docker compose -f docker/docker-compose.yml up -d
```

---

## Monitoring Access

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana Dashboard | http://localhost:3000 | `$GRAFANA_USER` / `$GRAFANA_PASSWORD` |
| Prometheus | http://localhost:9090 | — |
| Foxglove Studio | http://localhost:8765 | — |

---

## Port Reference

| Port | Service |
|------|---------|
| 8765 | Foxglove WebSocket bridge |
| 9090 | Prometheus metrics |
| 3000 | Grafana |
| 11435 | Ollama LLM (host-mapped) |
