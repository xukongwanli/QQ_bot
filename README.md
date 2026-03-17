# QQ Bot 666

An AI-powered QQ chatbot built with **NoneBot2** + **OneBot V11** adapter, using the **OpenAI-compatible API** (e.g. DeepSeek) for generating responses. Connects to the QQ account via a **Docker NapCat** framework.

## Features

- Responds to all private messages
- Responds to @mentions in group chats, with follow-up message buffering
- 15-second debounce: batches rapid-fire messages into a single AI request
- Image recognition support (downloads QQ CDN images and sends as base64)

## Tech Stack

- **NoneBot2** — async bot framework
- **OneBot V11** — QQ protocol adapter
- **NapCat (Docker)** — OneBot implementation for QQ connectivity
- **OpenAI SDK** — LLM API client (compatible with DeepSeek, GPT, etc.)

## Quick Start

1. Start the NapCat Docker container and log in to your QQ account.

2. Configure environment variables in `qqbot/.env`:
   ```
   OPENAI_API_KEY=your-api-key
   OPENAI_MODEL=gpt-4o
   ONEBOT_WS_URLS=["ws://127.0.0.1:3001"]
   ```

3. Install dependencies and run:
   ```bash
   cd qqbot
   pip install .
   nb run --reload
   ```

## Project Structure

```
qqbot/
├── pyproject.toml              # Dependencies & tool configs
├── .env / .env.dev             # Environment variables
└── src/plugins/
    └── main.py                 # Message handlers & AI logic
```

## License

MIT
