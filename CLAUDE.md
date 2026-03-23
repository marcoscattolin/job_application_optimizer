# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
uv venv
source .venv/Scripts/activate  # Windows: .\.venv\Scripts\activate
uv sync
```

API key must be placed at `secrets/openai_api_key.txt`.

## Running

```bash
# From file
uv run python -m code.run_optimizer --job ./job_posts/job_post.txt

# From stdin
cat job_post.txt | uv run python -m code.run_optimizer

# With options
uv run python -m code.run_optimizer --job job_post.txt --lang IT --model-writer gpt-4o

# As installed CLI
job-optimizer --job job_post.txt
```

Key CLI flags: `--lang IT|EN`, `--model-structured`, `--model-writer`, `--out`, `--log-level`.

## Architecture

Three-agent sequential pipeline: **Scout → Strategy → Writer**

1. **ScoutAgent** (`agents/scout_agent.md`) — extracts a structured `JobSpec` (Pydantic model) from raw job text using `responses.parse()` for guaranteed JSON
2. **StrategyAgent** (`agents/strategy_agent.md`) — evaluates fit (0–100 score), decides APPLY/MAYBE/SKIP, selects narrative assets, outputs `ApplicationPlan` via `responses.parse()`
3. **WriterAgent** (`agents/writer_agent.md`) — generates cover letter, targeted CV, and optional headhunter email as free-form Markdown using `responses.create()`

Each agent is stateless; the orchestrator (`code/run_optimizer.py`) passes accumulated context down the chain. Outputs land in `outputs/{job_name}/{YYYYMMDD_HHMMSS}/`.

### Key design decisions

- **Pydantic schemas** (`code/models.py`) enforce structure and prevent hallucination in Scout/Strategy outputs
- **System prompts live in `agents/*.md`** — edit them without touching Python code. Alternative strategy modes (`aggressive_v1.md`, `conservative_v1.md`) are swappable
- **`bio/BIOGRAPHY_PROFILE.md`** is the single source of truth injected into all agents — never duplicate profile data in prompts
- `--model-structured` controls Scout/Strategy; `--model-writer` controls Writer — useful to trade cost vs. quality independently
