# 7-Day Enterprise Onboarding & Pilot Playbook

> **Target Timeline:** 1 Week (Day 1 to Day 7)  
> **Objective:** Successfully deploy a production-grade Pilot / Proof-of-Concept (PoC) for an enterprise customer using **FrontierX** & **NexusOS**.

---

## 📅 Day-by-Day Onboarding Schedule

```
┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐
│   DAY 1   │──►│   DAY 2   │──►│   DAY 3   │──►│   DAY 4   │──►│   DAY 5   │──►│   DAY 6   │──►│   DAY 7   │
│ Discovery │   │ Security  │   │ Hardware  │   │ Mission   │   │ Safety &  │   │ Exec Live │   │ Pilot     │
│ & Scoping │   │ & Sandbox │   │ Bridging  │   │ Brain     │   │ Watchdog  │   │ Demo Day  │   │ Handoff   │
└───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘   └───────────┘
```

---

### 🔹 Day 1: Discovery, Technical Scoping & Pilot Agreement
**Goal:** Lock in scope, success metrics, and infrastructure requirements.

1. **Send the Technical Intake Questionnaire** (see section below).
2. **Align on Pilot Success Criteria:**
   - Define **1 to 2 specific mission scenarios** (e.g. *"Autonomous inspection of facility generators + live telemetry in Web UI"* or *"Multi-robot task handoff between mobile rover and stationary arm"*).
   - Agree on measurable KPIs: e.g. `<50ms` telemetry latency, `100%` safety E-Stop reliability, `99.9%` uptime during test window.
3. **Sign a lightweight Pilot Agreement / Evaluation MoU:**
   - Duration: 14 to 30 days.
   - Commercial pilot fee or agreed conversion price to annual license upon hitting KPIs.
4. **Establish Communications:**
   - Create a dedicated Slack / Teams Connect channel (`#frontierx-<company>-pilot`).

---

### 🔹 Day 2: Security, Architecture & Sandbox Provisioning
**Goal:** Spin up isolated client sandbox environments with enterprise security.

1. **Deploy Customer Sandbox Instance:**
   - Run deployment script with production overlay:
     ```bash
     export ROS_DOMAIN_ID=42
     export GRAFANA_PASSWORD="<CustomerSecurePassword>"
     ./scripts/deploy.sh prod
     ```
   - Or deploy via Helm on customer EKS/GKE cluster using [deploy/helm/frontierx/](file:///c:/Users/ASUS/Downloads/robot/deploy/helm/frontierx/).
2. **Generate Client Credentials & API Keys:**
   - Issue client-scoped JWT tokens and `X-API-Key` headers via [auth.py](file:///c:/Users/ASUS/Downloads/robot/src/frontierx_brain/frontierx_brain/api/auth.py).
   - Configure customer IP whitelists on the rate limiter.
3. **Verify Security Baseline:**
   - Confirm all containers run as non-root (`frontierx` UID=1000).
   - Validate read-only root filesystems and Docker secret bindings.

---

### 🔹 Day 3: Hardware Integration & HAL Plugin Setup
**Goal:** Connect customer robots (or digital twins) to NexusOS / FrontierX.

1. **Determine Hardware Mode:**
   - **Mode A (Physical Robots):** Install `pip install nexusos-fleet` on robot compute (Jetson / x86 / Raspberry Pi) or write custom [AbstractHardwarePlugin](file:///c:/Users/ASUS/Downloads/NexusOS/hal/base.py) (e.g. CAN bus, ODrive, serial motor driver).
   - **Mode B (ROS 2 Fleet):** Run [ros2_bridge.py](file:///c:/Users/ASUS/Downloads/NexusOS/hal/bridges/ros2_bridge.py) to map their existing `/cmd_vel`, `/odom`, and `/joint_states` topics.
   - **Mode C (Simulation / Digital Twin):** Spin up the pre-packaged Isaac Sim / Gazebo simulation stack.
2. **Verify Telemetry Stream:**
   - Confirm high-frequency msgpack streaming at 20-50 Hz on `/ws/telemetry/<robot_id>`.
   - Inspect robot cards appearing in real-time on the Fleet Dashboard at `http://<sandbox-ip>:8000`.

---

### 🔹 Day 4: Central Brain & Mission World Model Configuration
**Goal:** Map the customer's physical environment and define domain skills.

1. **Populate Customer World Model:**
   - Seed their facility objects, charging docks, inspection targets, and workbenches via REST API:
     ```bash
     curl -X POST http://<server>:8000/api/v1/world/object \
       -H "X-API-Key: <client-key>" \
       -H "Content-Type: application/json" \
       -d '{"object_id":"pump_01","class_name":"water_pump","x":12.5,"y":4.2,"z":0.0,"status":"UNINSPECTED"}'
     ```
2. **Configure AI Task Planner & LLM Backend:**
   - If on-premise air-gapped: Point `OLLAMA_BASE_URL` to local Ollama (Llama 3.1).
   - If cloud connected: Configure `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` in `docker/.secrets/`.
3. **Run Dry-Run Natural Language Commands:**
   - Submit natural language tasks via `/api/v1/command` and verify plan generation and skill decomposition.

---

### 🔹 Day 5: Safety Interlocks, Watchdogs & Observability
**Goal:** Perform mandatory safety stress tests and verify Grafana metrics.

1. **Execute Safety Interlock Drill:**
   - **Network Cut Test:** Disconnect network during autonomous mission; verify watchdog triggers `EMERGENCY_STOP` within 2 seconds.
   - **Speed Clamping Test:** Submit out-of-spec velocity command; verify policy supervisor clamps linear speed to configured safety limits.
   - **Global E-Stop Test:** Trigger `/api/v1/safety/e_stop` and confirm all actuators freeze immediately.
2. **Verify Monitoring & Alerting:**
   - Open Grafana at `http://<server>:3000` (pre-configured [frontierx.json](file:///c:/Users/ASUS/Downloads/robot/docker/monitoring/grafana/dashboards/frontierx.json)).
   - Verify Prometheus scrapes on `:9090` are capturing task throughput, planning latency, and robot battery states.

---

### 🔹 Day 6: Executive Live Demonstration & Technical Review
**Goal:** Run the live end-to-end pilot demo for key enterprise stakeholders.

1. **Demo Agenda (30 Mins):**
   - **Min 00–05:** Architecture Overview (Heterogeneous Fleet + Central Brain).
   - **Min 05–15:** Live Mission Execution (Natural language command -> Multi-body coordination -> Real-time 2D map & gauges).
   - **Min 15–20:** Safety & Diagnostics Demonstration (E-Stop, battery drain alerts, Prometheus metrics).
   - **Min 20–30:** Q&A, KPI review, and pilot access handoff.
2. **Provide Stakeholder Access:**
   - Distribute Dashboard URLs, individual user logins, and API Swagger UI links (`/docs`).

---

### 🔹 Day 7: Pilot Handoff, SLA & Commercial Conversion Review
**Goal:** Formal pilot kickoff with dedicated support and scheduled milestones.

1. **Handoff Documentation Package:**
   - NexusOS User Guide ([USERGUIDE.md](file:///c:/Users/ASUS/Downloads/NexusOS/USERGUIDE.md)).
   - Deployment Runbook ([deployment.md](file:///c:/Users/ASUS/Downloads/robot/docs/runbooks/deployment.md)).
   - Incident Response Runbook ([incident-response.md](file:///c:/Users/ASUS/Downloads/robot/docs/runbooks/incident-response.md)).
2. **Schedule Weekly KPI Check-ins:**
   - Set up 15-minute weekly standup to review task memory reports and system telemetry.
3. **Lock Commercial Target Date:**
   - Agree on Day 30 pilot sign-off and annual license conversion.

---

## 📋 Client Intake Questionnaire (Send Today)

Copy and email this to the client lead immediately:

```markdown
Hi [Client Name],

We are excited to kick off the FrontierX / NexusOS enterprise pilot with your team. 
To ensure we have your isolated sandbox environment and hardware connectors ready for Day 2, please provide the following details:

1. Target Deployment Environment:
   [ ] Cloud Managed (AWS / GCP / Azure Kubernetes - EKS/GKE/AKS)
   [ ] On-Premise Bare-Metal Server (Ubuntu 22.04 + Docker)
   [ ] Air-Gapped Edge Node (Jetson Orin / Local compute)

2. Fleet & Hardware Overview:
   - Number of robot bodies to connect during pilot: [ e.g., 2 rovers, 1 arm ]
   - Robot hardware/communication protocol: [ e.g., ROS 2 Humble / Modbus / CAN / Serial / Custom REST ]
   - Do you have existing URDF or 2D floor maps (.yaml / .pgm / CAD)?

3. Primary Pilot Objective / Use Case:
   - What is the #1 automated mission or workflow you want validated during this pilot?

4. Security & Compliance Requirements:
   - Required SSO / Auth provider (JWT, OAuth2, Okta, LDAP): [ ]
   - LLM preference: [ ] Local Air-Gapped (Ollama)  [ ] Cloud API (OpenAI / Anthropic)

5. Core Pilot Team:
   - Primary Technical Contact (Name, Email, Slack/Teams handle):
   - Executive Sponsor (Name, Title):

Best regards,
[Your Name]
FrontierX Robotics Engineering Team
```

---

## 📦 Deliverables Packaging Checklist

Ensure the client receives these assets in their onboarding email:

| Asset | Path / Reference | Purpose |
|-------|-------------------|---------|
| **NexusOS User Guide** | [USERGUIDE.md](file:///c:/Users/ASUS/Downloads/NexusOS/USERGUIDE.md) | Fleet orchestration & HAL plugin guide |
| **API Reference (OpenAPI/Swagger)** | `http://<sandbox-ip>:8000/docs` | Interactive REST API explorer |
| **Fleet Dashboard** | `http://<sandbox-ip>:8000` | Real-time map, telemetry & teleoperation |
| **Grafana Monitoring** | `http://<sandbox-ip>:3000` | Operational KPIs & safety metrics |
| **Deployment Runbook** | [deployment.md](file:///c:/Users/ASUS/Downloads/robot/docs/runbooks/deployment.md) | IT/DevOps infrastructure setup |
| **Incident Response Runbook** | [incident-response.md](file:///c:/Users/ASUS/Downloads/robot/docs/runbooks/incident-response.md) | Safety procedures & troubleshooting |
| **PyPI Package** | `pip install nexusos-fleet` | Edge agent client library |
