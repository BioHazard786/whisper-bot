# Psst! 🤫 — Modern Telegram Whisper Bot

A high-performance, privacy-focused Telegram Whisper Bot built with **Python 3.11+**, **`aiogram` v3**, and **Telegram Bot API Ephemeral Messages**.

---

## ✨ Features

- **Inline Whispers (Any Chat)**: Send locked whisper cards anywhere across Telegram via `@psst_whisper_bot @recipient secret`.
- **Multi-Recipient Whispers**: Whisper to multiple users at once (`@alice @bob @charlie secret` or `12345678 87654321 secret`).
- **User IDs & Telegram Links**: Full support for raw numeric user IDs (`12345678`), ID prefixes (`id:12345678`), and deep links (`[Name](tg://user?id=12345678)`).
- **One-Time Self-Destruct Whispers**: Whispers that permanently destroy themselves once opened by the intended recipient(s) (`!1`).
- **Telegram Bot API Ephemeral Commands**: Group commands registered with `is_ephemeral=True` so your `/whisper` commands remain invisible to other group members.
- **Telegram Bot API Ephemeral Delivery**: Delivers the whisper directly onto the recipient's timeline in groups using `ephemeral_message_parameters`.
- **Private Fallback Modals**: Seamless fallback to Telegram secure alert popups for inline messages and legacy clients.
- **Structured Logging (`structlog`)**: Real-time request context tracking, latency measurements, and production JSON mode.
- **Strict Typing & Linting**: 100% compliant with `pyright` and `ruff`.
- **Ultra-Lightweight Container**: Minimal multi-stage Alpine Docker image (~32 MB).

---

## ⚙️ @BotFather Configuration

To enable inline whispers anywhere across Telegram:
1. Message [@BotFather](https://t.me/botfather) and send `/setinline`.
2. Select your bot.
3. Enter placeholder text: `Type: @recipient secret message`.
4. *(Optional)* Send `/setprivacy` -> Select your bot -> choose **Disable** so the bot can also read mentions when added to groups.

---

## 📖 Operational Modes

Psst! works across two distinct modes:

### 1. Inline Query Mode (`@psst_whisper_bot`)
Works anywhere across Telegram (groups, private chats, channels) by typing in the chat bar and selecting a card:
```text
@psst_whisper_bot @alice @bob The secret password is 1234
@psst_whisper_bot 12345678 87654321 Meeting at dusk
@psst_whisper_bot !1 @alice Self-destructing credentials
```

### 2. Group Command Mode (`/whisper`)
For groups where Psst! is added as a member:
```text
/whisper @alice @bob The meeting link is ready
/whisper 12345678,87654321 Sensitive project notes
```
- Commands are invisible to other members thanks to Bot API `is_ephemeral=True`.
- Whispers are delivered directly onto the recipient's timeline using `ephemeral_message_parameters`.
- You can also reply to any message in the group with `/whisper your secret`.

---

## 👥 Advanced Targeting & Formats

You can mix and match targets in any combination:

| Format | Example | Description |
|---|---|---|
| **Multiple Usernames** | `@alice @bob @charlie` | Multiple username recipients |
| **Numeric User IDs** | `12345678 87654321` | Targets users by immutable Telegram ID |
| **Comma-separated IDs** | `12345678,87654321` | Comma-separated user IDs |
| **Prefixed IDs** | `id:12345678 uid:87654321` | Explicit ID prefixes |
| **Telegram Deep Links** | `[John](tg://user?id=12345678)` | Mention links for users without usernames |
| **Mixed Targets** | `@alice 12345678 id:99999999` | Mix usernames and IDs freely |
| **One-Time Flag** | `!1 @alice secret` | Self-destructs permanently after opening |
| **Hide Sender Flag** | `!nosender @alice secret` | Disallows sender from re-opening |

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
