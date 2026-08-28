#!/usr/bin/env bash
# =============================================================================
# FrontierX Deploy Script
# =============================================================================
# Usage: ./scripts/deploy.sh [dev|staging|prod]
#
# Validates required environment variables, selects the correct
# docker-compose override, launches the stack, and verifies health.
# =============================================================================

set -euo pipefail

ENV="${1:-dev}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_BASE="$PROJECT_ROOT/docker/docker-compose.yml"

# ── Colour helpers ────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

info "=== FrontierX Deploy — Environment: $ENV ==="

# ── Validate environment argument ─────────────────────────────
case "$ENV" in
  dev|staging|prod) ;;
  *) error "Unknown environment '$ENV'. Use: dev | staging | prod" ;;
esac

# ── Select compose override ───────────────────────────────────
OVERRIDE_FILE="$PROJECT_ROOT/docker/docker-compose.override.${ENV}.yml"
if [[ -f "$OVERRIDE_FILE" ]]; then
  COMPOSE_CMD="docker compose -f $COMPOSE_BASE -f $OVERRIDE_FILE"
  info "Using override: $OVERRIDE_FILE"
else
  COMPOSE_CMD="docker compose -f $COMPOSE_BASE"
  warn "No override file found for '$ENV' — using base compose only"
fi

# ── Required environment variables ───────────────────────────
REQUIRED_VARS=(
  ROS_DOMAIN_ID
)
MISSING=()
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    MISSING+=("$var")
  fi
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
  error "Missing required environment variables: ${MISSING[*]}"
fi

# ── Production safety checks ──────────────────────────────────
if [[ "$ENV" == "prod" ]]; then
  info "Production pre-flight checks..."
  [[ -z "${GRAFANA_PASSWORD:-}" ]] && error "GRAFANA_PASSWORD must be set in prod"
  [[ "${GRAFANA_PASSWORD:-}" == "frontierx" ]] && \
    error "GRAFANA_PASSWORD is set to the default. Change it before deploying to prod."
fi

# ── Inject build metadata ─────────────────────────────────────
export BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export REVISION="$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
export VERSION="$(git describe --tags --always 2>/dev/null || echo 'dev')"
info "Build metadata: VERSION=$VERSION  REVISION=$REVISION"

# ── Deploy ────────────────────────────────────────────────────
info "Pulling latest images..."
$COMPOSE_CMD pull --ignore-pull-failures 2>/dev/null || true

info "Starting stack..."
$COMPOSE_CMD up --build -d

# ── Wait and health-check ─────────────────────────────────────
info "Waiting 15s for services to start..."
sleep 15

info "Running post-deploy health checks..."
"$SCRIPT_DIR/healthcheck.sh"

info "=== Deploy complete (env=$ENV, version=$VERSION) ==="
