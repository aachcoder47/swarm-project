# Secret Rotation Runbook

> **Audience:** DevOps / Security engineers
> **Last updated:** 2026-08-29

This document outlines the standard operational procedure for rotating API keys and passwords in the FrontierX robotics platform without causing operational downtime.

---

## 1. Secret Catalog

The following secrets must be rotated periodically:

| Secret Name | Location | Impact | Rotation Frequency |
|-------------|----------|--------|-------------------|
| `OPENAI_API_KEY` | `docker/.secrets/openai_api_key` | LLM agent planning failures | 90 days |
| `ANTHROPIC_API_KEY` | `docker/.secrets/anthropic_api_key` | LLM agent planning failures | 90 days |
| `GRAFANA_PASSWORD` | Docker environment / Vault | Monitoring dashboard login lock | 180 days |
| `FRONTIERX_JWT_SECRET` | Environment variable | API token verification failures | 180 days |
| `FRONTIERX_API_KEYS` | Environment variable | Robot connection heartbeat failures | 180 days |

---

## 2. API Key Rotation (OpenAI / Anthropic)

### Step 1: Generate New Key
Generate a new API key in the respective cloud provider console (e.g. OpenAI Platform / Anthropic Console). Do **not** revoke the old key yet.

### Step 2: Update Secret File
Write the new key to the Docker secrets directory:

```bash
echo -n "new-api-key-here" > docker/.secrets/openai_api_key
```

### Step 3: Rolling Restart of Agent
Since the agent container reads secrets at startup, perform a restart:

```bash
docker compose -f docker/docker-compose.yml restart agent
```

### Step 4: Verify Agent Logs
Verify the agent successfully starts and connects to Ollama/OpenAI using the new key:

```bash
docker logs frontierx_agent --tail 50
```

### Step 5: Revoke Old Key
After confirming the agent is operational and planning successfully, delete/revoke the old key from the provider console.

---

## 3. JWT Secret Rotation (Zero-Downtime)

To rotate the `FRONTIERX_JWT_SECRET` variable without invalidating active user sessions:

1. **Phase 1: Dual-Key Support (Planned):** Configure the gateway to accept the new secret for signature verification while using the new secret to sign new tokens.
2. **Phase 2: Update Environment:**
   Update the `FRONTIERX_JWT_SECRET` env var in `docker/.env`.
3. **Phase 3: Rollout:**
   Perform a rolling restart of the API gateway.
   ```bash
   docker compose -f docker/docker-compose.yml restart ros2-core
   ```
4. **Phase 4: Force Logout:** Users will be prompted to log in again once their old-token expires.

---

## 4. Emergency Rotation Playbook

In the event of a secret leak:
1. Revoke the key immediately at the provider side.
2. Generate a new key.
3. Apply to `docker/.secrets/` or `docker/.env`.
4. Run:
   ```bash
   ./scripts/deploy.sh prod
   ```
5. Confirm all systems are operational with `./scripts/healthcheck.sh`.
