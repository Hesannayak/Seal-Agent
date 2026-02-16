# Seal-Agent

**The Claude of Sales** — A self-learning, evolving AI sales agent.

Seal-Agent is a highly specialized AI sales agent capable of performing everything a world-class sales professional can do. It integrates with any sales tool, communication platform, or CRM, operating autonomously 24/7 while continuously improving from every interaction.

## Architecture

```
Soul System (soul/)     →  Agent identity, style, playbook, memory rules
Core Runtime (core/)    →  Agent orchestrator, heartbeat, memory, reasoning
Skills (skills/)        →  Prospecting, outreach, deals, negotiation
Integrations (integrations/)  →  CRM, email, LinkedIn, calendar, etc.
API (api/)              →  REST + WebSocket endpoints
CLI (cli/)              →  Command-line interface
```

## Quick Start

### Prerequisites

- Python 3.12+
- Docker & Docker Compose
- An Anthropic API key

### Setup

```bash
# Clone and enter the project
git clone <repo-url>
cd seal-agent

# Copy environment config
cp .env.example .env
# Edit .env with your Anthropic API key

# Start with Docker Compose
docker compose up -d

# Or run locally
pip install -e ".[dev]"
seal start
```

### CLI Commands

```bash
seal start        # Start the agent server
seal chat "msg"   # Send a message to the agent
seal status       # Check agent status
seal soul         # View agent identity
```

### API

Once running, the API is available at `http://localhost:8000`:

- `GET /health` — Health check
- `POST /api/agent/chat` — Chat with the agent
- `GET /api/agent/status` — Agent status
- `GET /api/deals/pipeline` — View pipeline
- `POST /api/prospects/` — Create prospect

Full API docs at `http://localhost:8000/docs`.

## The Soul System

The agent's behavior is defined by markdown files in `soul/`:

| File | Purpose |
|------|---------|
| `soul.md` | Core identity, values, ethical boundaries |
| `heartbeat.md` | Autonomous operational rhythm |
| `style.md` | Communication style and tone |
| `memory.md` | How the agent stores and recalls knowledge |
| `playbook.md` | Sales strategies and tactics |
| `evolution.md` | Self-learning and adaptation rules |

Edit these files to customize the agent's behavior without changing code.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Project Status

This project is in active development. See [PLAN.md](PLAN.md) for the full roadmap.
