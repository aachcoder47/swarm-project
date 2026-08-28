#!/usr/bin/env bash
# =============================================================================
# FrontierX Post-Deploy Health Check
# =============================================================================
# Verifies that all expected services are alive after a deployment.
# Exits with code 1 if any check fails.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0

pass() { echo -e "${GREEN}  PASS${NC}  $*"; ((PASS++)); }
fail() { echo -e "${RED}  FAIL${NC}  $*"; ((FAIL++)); }
info() { echo -e "${YELLOW}  ....${NC}  $*"; }

echo "=== FrontierX Health Checks ==="

# ── Foxglove WebSocket bridge ────────────────────────────────
info "Checking Foxglove WebSocket bridge (:8765)..."
if timeout 5 bash -c "echo > /dev/tcp/localhost/8765" 2>/dev/null; then
  pass "Foxglove WebSocket bridge reachable on :8765"
else
  fail "Foxglove WebSocket bridge NOT reachable on :8765"
fi

# ── Docker container health states ───────────────────────────
info "Checking Docker container health states..."
CONTAINERS=(
  frontierx_ros2_core
  frontierx_navigation
  frontierx_foxglove
)

for container in "${CONTAINERS[@]}"; do
  STATUS=$(docker inspect --format='{{.State.Status}}' "$container" 2>/dev/null || echo "missing")
  HEALTH=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container" 2>/dev/null || echo "missing")

  if [[ "$STATUS" == "running" ]]; then
    if [[ "$HEALTH" == "healthy" || "$HEALTH" == "no-healthcheck" ]]; then
      pass "$container: $STATUS ($HEALTH)"
    else
      fail "$container: $STATUS but health=$HEALTH"
    fi
  else
    fail "$container: $STATUS"
  fi
done

# ── Prometheus (if monitoring profile active) ─────────────────
if docker ps --format '{{.Names}}' | grep -q frontierx_prometheus; then
  info "Checking Prometheus (:9090)..."
  if curl -sf "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
    pass "Prometheus healthy"
  else
    fail "Prometheus NOT healthy"
  fi
fi

# ── Grafana (if monitoring profile active) ────────────────────
if docker ps --format '{{.Names}}' | grep -q frontierx_grafana; then
  info "Checking Grafana (:3000)..."
  if curl -sf "http://localhost:3000/api/health" > /dev/null 2>&1; then
    pass "Grafana healthy"
  else
    fail "Grafana NOT healthy"
  fi
fi

# ── Summary ──────────────────────────────────────────────────
echo ""
echo "=== Health Check Summary: ${PASS} passed, ${FAIL} failed ==="

if [[ $FAIL -gt 0 ]]; then
  echo -e "${RED}Deploy health checks FAILED. Check logs above.${NC}"
  exit 1
else
  echo -e "${GREEN}All health checks passed!${NC}"
  exit 0
fi
