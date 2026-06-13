# NetSage — AI Network Engineer Agent

An AI chat agent that operates real networking tools instead of just talking. Ask it about your network health, plan subnets, or audit Cisco configs — it calls live tools and shows its work.

![NetSage demo](docs/demo.gif)

---

## What It Does

NetSage is a Claude-powered agent with four built-in network engineering tools:

| Tool | What it does |
|------|-------------|
| `get_devices` | Fetches all devices from NetPulse with status, latency, and uptime |
| `get_device_history(ip)` | Returns latency history for a specific device |
| `plan_subnets(base_cidr, requirements)` | VLSM allocation — largest-first, power-of-2 sizing |
| `audit_config(config_text)` | Checks Cisco IOS configs for security issues with remediation commands |

The agent never guesses — it always calls a tool for facts it can look up or compute.

---

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│   React Frontend    │  HTTP   │   NetSage Backend    │
│  (Vite + TypeScript)│────────▶│   (FastAPI, Python)  │
│                     │◀────────│   Agent loop         │
│  - Chat UI          │ stream  │   Claude claude-sonnet-4-6│
│  - Tool call chips  │         │   Tool executor      │
└─────────────────────┘         └──────────┬───────────┘
                                           │ HTTP
                                           ▼
                                ┌──────────────────────┐
                                │   NetPulse Backend   │
                                │   (FastAPI, Python)  │
                                │   /api/devices       │
                                │   /api/devices/{ip}  │
                                │     /history         │
                                │   /ws (WebSocket)    │
                                └──────────────────────┘
```

**Agent loop:** Frontend sends conversation history → NetSage backend streams tool-call events and text back → UI renders tool chips inline as collapsible steps.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Anthropic API key

### 1. Clone & set up NetPulse (network monitor)

```bash
git clone <repo-url>
cd netpulse
pip install -r requirements.txt
```

Start in demo mode (simulates 8 devices):
```bash
# Windows
$env:DEMO="1"; python -m uvicorn backend.main:app --port 8002

# macOS/Linux
DEMO=1 python -m uvicorn backend.main:app --port 8002
```

### 2. Set up NetSage (AI agent)

```bash
cd ../netsage
pip install -r requirements.txt
cp .env.example .env
# Add your Anthropic API key to .env
```

Start the agent backend:
```bash
python -m uvicorn backend.app:app --port 8004
```

### 3. Build and serve the frontend

```bash
cd frontend
npm install
npm run build
npx serve dist --listen 5174
```

Open **http://localhost:5174**

---

## Environment Variables

### NetSage `.env`
```
ANTHROPIC_API_KEY=sk-ant-...
NETPULSE_BASE=http://localhost:8002
```

### NetPulse environment flags
| Variable | Default | Description |
|----------|---------|-------------|
| `DEMO` | `""` | Set to `"1"` for simulated devices |
| `SUBNET` | `192.168.1.0/24` | Subnet to scan in live mode |
| `INTERVAL` | `10` | Scan interval in seconds |

---

## Example Prompts

```
What's the health of my network?
Why is the printer slow?
Plan subnets for Staff 60 / Students 100 / IoT 20 on 192.168.1.0/24
Audit this config: [paste Cisco IOS config]
```

---

## Project Structure

```
netsage/
├── backend/
│   ├── app.py          # FastAPI app, /api/chat endpoint, streaming
│   ├── agent.py        # Claude agent loop, tool dispatch
│   ├── tools.py        # Tool implementations (get_devices, plan_subnets, audit_config)
│   └── __init__.py
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Chat layout
│   │   ├── api.ts          # Streaming fetch to /api/chat
│   │   ├── types.ts        # Message/tool types
│   │   └── components/     # MessageBubble, ToolChip
│   └── dist/               # Production build
├── tests/
├── .env.example
├── SPEC.md
└── README.md

netpulse/
├── backend/
│   ├── main.py         # FastAPI app, /api/devices, /ws
│   ├── scanner.py      # DeviceStore, ping scanner, run_monitoring_loop
│   ├── demo.py         # DEMO_DEVICES, run_demo_loop
│   └── models.py       # DeviceInfo, DeviceHistory, LatencySample
└── frontend/
    └── src/
        └── hooks/
            └── useDevices.ts   # WebSocket connection to NetPulse
```

---

## Tech Stack

| Layer | Tech |
|-------|------|
| AI | Anthropic claude-sonnet-4-6 (tool use) |
| Agent backend | Python, FastAPI, httpx, python-dotenv |
| Network monitor | Python, FastAPI, asyncio, WebSockets |
| Frontend | React, TypeScript, Vite |
| Subnet math | Pure Python (VLSM, largest-first) |
| Config audit | Regex-based Cisco IOS parser |

---

## Skills Demonstrated

- **Agentic AI** — multi-turn tool-use loop with Claude, streaming responses
- **Full-stack** — Python FastAPI backend + React/TypeScript frontend
- **Networking** — VLSM subnetting, Cisco IOS config auditing, live ICMP ping scanner
- **Real-time** — WebSocket device monitor with latency sparklines
- **Systems** — async Python, subprocess management, concurrent ping scanner

---

## Author

Muhammed Isa Loonat — Computer Engineering student, Istinye University  
[GitHub](https://github.com/misaloonat) · [LinkedIn](https://linkedin.com/in/misaloonat)
