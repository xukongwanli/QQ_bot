# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

QQ chatbot built with **NoneBot2** + **OneBot V11 adapter**, using **DeepSeek API** (via OpenAI SDK) for AI-powered responses. The bot handles both private messages (all) and group messages (when @mentioned).

## Commands

All commands run from the `qqbot/` directory:

```bash
# Run the bot (with hot-reload)
nb run --reload

# Lint & format
ruff check .
ruff format .

# Type checking
pyright
```

## Architecture

```
qqbot/
├── pyproject.toml          # Dependencies, NoneBot config, ruff/pyright settings
├── .env / .env.dev         # Environment config (DEEPSEEK_API_KEY, ports, WS URLs)
└── src/plugins/
    └── main.py             # All message handlers live here
```

- **NoneBot2** auto-discovers plugins in `src/plugins/`. The `nb` CLI handles startup via FastAPI + Uvicorn.
- **Message flow:** QQ client → OneBot V11 (WebSocket) → NoneBot2 → plugin handler → DeepSeek API → reply
- Two handlers: `handle_private_message` (all private msgs, priority 10) and `handle_group_message` (`to_me()` rule for @mentions, priority 10).

## Configuration

Environment variables in `.env` files:
- `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL` — LLM credentials
- `ONEBOT_WS_URLS` — WebSocket endpoint for OneBot protocol (default: `ws://127.0.0.1:3001`)
- `DRIVER=~fastapi`, `HOST=0.0.0.0`, `PORT=8080`

## Linting Rules

Ruff is configured with extensive rules (40+ categories). Key ignored rules:
- `E402` — NoneBot's `require()` pattern needs imports after top-level
- `B008` — NoneBot's `Depends()` pattern uses function calls in defaults
- Line length: 88, target Python version: 3.9
