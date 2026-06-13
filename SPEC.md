\# NetSage — AI Network Engineer Agent



A chat agent that operates real networking tools instead of just talking.

Python/FastAPI backend runs an agent loop against the Anthropic API (tool use);

React frontend is a chat UI that shows the agent's tool calls as steps.



\## Tools the agent can use

1\. get\_devices() — calls the NetPulse API (http://localhost:8000/api/devices),

&#x20;  returns device list with status, latency, uptime

2\. get\_device\_history(ip) — calls NetPulse /api/devices/{ip}/history

3\. plan\_subnets(base\_cidr, requirements\[]) — VLSM allocation implemented in

&#x20;  Python (largest-first, power-of-2 sizing, hosts+2); returns full table

4\. audit\_config(config\_text) — checks a Cisco IOS config for security issues:

&#x20;  telnet on VTY, missing service password-encryption, plaintext passwords,

&#x20;  missing enable secret, ip http server enabled, missing access-class on VTY.

&#x20;  Returns findings with severity and remediation commands.



\## Backend (backend/, Python, FastAPI)

\- Agent loop: send conversation + tool schemas to Anthropic API

&#x20; (claude-sonnet-4-6), execute requested tool calls locally, feed results

&#x20; back, repeat until the model produces a final answer

\- POST /api/chat — accepts conversation history, streams back assistant text

&#x20; AND tool-call events (so the UI can show "calling get\_devices...")

\- ANTHROPIC\_API\_KEY read from .env (python-dotenv); .env in .gitignore;

&#x20; provide .env.example

\- System prompt: "You are NetSage, a network engineering assistant. Always

&#x20; use tools for facts about the network, subnet math, or config audits —

&#x20; never guess values you can compute or look up."

\- pytest tests for all four tool functions (mock the NetPulse HTTP calls)

\- Graceful behavior if NetPulse isn't running: tool returns a clear error

&#x20; the agent can relay



\## Frontend (frontend/, React + Vite + TypeScript)

\- Chat UI: message list, input box, streaming assistant responses

\- Tool calls rendered inline as collapsible step chips

&#x20; ("🔧 plan\_subnets …" → expandable to show input/result JSON)

\- A few suggested starter prompts as clickable chips:

&#x20; "What's the health of my network?", "Why is any device down?",

&#x20; "Plan subnets for Staff 60 / Students 100 / IoT 20 on 192.168.1.0/24",

&#x20; "Audit this config: \[paste]"

\- Dark theme, responsive



\## Quality

\- Tool functions pure and separately testable from the agent loop

\- README: architecture diagram, demo GIF, setup with .env.example, cost note

