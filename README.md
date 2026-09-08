# Psst! 🤫 — Modern Telegram Whisper Bot

A high-performance, privacy-focused Telegram Whisper Bot built with **Python 3.11+**, **`aiogram` v3**, and **Telegram Bot API Ephemeral Messages**.

---

## ✨ Features

- **Inline Whispers (Any Chat)**: Send locked whispers in group chats, private messages, or channels without needing bot admin rights (`@psst_whisper_bot @recipient secret`).
- **Multi-Recipient Whispers (Normal & Inline)**: Whisper to multiple targets at once (`@alice @bob @charlie secret`). Supported across both inline and group modes!
- **One-Time Self-Destruct Whispers**: Whispers that permanently destroy themselves once opened by the intended recipient(s).
- **Telegram Bot API Ephemeral Commands**: Group commands registered with `is_ephemeral=True` so your `/whisper` commands remain invisible to other group members.
- **Telegram Bot API Ephemeral Delivery**: Delivers the whisper directly onto the recipient's timeline in groups using `ephemeral_message_parameters`.
- **Private Fallback Modals**: Seamless fallback to Telegram secure alert popups for inline messages and legacy clients.
- **Structured Logging (`structlog`)**: Real-time request context tracking, latency measurements, and production JSON mode.
- **Strict Typing & Linting**: 100% compliant with `pyright` and `ruff`.
- **Ultra-Lightweight Container**: Minimal multi-stage Alpine Docker image (~32 MB).

---

## 👥 Multi-Recipient Whispers

Psst! natively supports multiple recipients in **both** operational modes:

### 1. Inline Mode (`@psst_whisper_bot`)
```
@psst_whisper_bot @alice @bob @charlie The server password is secret
```
- A locked card is generated for `@alice`, `@bob`, and `@charlie`.
- All three authorized recipients (and the sender) can open the whisper.
- Unauthorized users will be blocked with an alert.
- For **one-time whispers** (`!1 @alice @bob`), each recipient can view their copy once; the whisper permanently self-destructs once all specified recipients have read it!

### 2. Group Command Mode (`/whisper`)
```
/whisper @alice @bob The meeting link is in your inbox
```
- Sent invisibly using Telegram Ephemeral Commands.
- An ephemeral prompt is posted for `@alice` and `@bob`.
- When either recipient clicks the button, Telegram renders the message on that specific recipient's chat timeline ephemerally!

---

## 🚀 Quick Start

### Option A: Running with `uv` (Local Development)

1. **Clone and setup virtual environment:**
   ```bash
   uv sync
   ```

2. **Configure `.env`:**
   ```bash
   cp .env.sample .env
   # Edit .env and set your BOT_TOKEN
   ```

3. **Run the bot:**
   ```bash
   uv run whisper-bot
   ```

---

### Option B: Running with Docker & Docker Compose

Psst! includes an optimized multi-stage `Dockerfile` based on `python:3.11-alpine` (~32 MB total image size).

1. **Configure `.env`:**
   ```bash
   cp .env.sample .env
   # Set BOT_TOKEN=your_token_here
   ```

2. **Start the container in the background:**
   ```bash
   docker compose up -d
   ```

3. **View container logs:**
   ```bash
   docker compose logs -f
   ```

4. **Stop the container:**
   ```bash
   docker compose down
   ```

---

## 🛠️ Developer Tooling

- **Run Tests**: `uv run pytest -v`
- **Lint Code**: `uv run ruff check .`
- **Format Code**: `uv run ruff format .`
- **Type Check**: `uv run pyright`

For full architectural details, code conventions, and extension protocols, see [AGENTS.md](file:///home/zaid/Documents/Personal%20Projects/whisper-bot/AGENTS.md).
