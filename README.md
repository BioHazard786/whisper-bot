# Psst! 🤫 — Modern Telegram Whisper Bot

A high-performance, privacy-focused Telegram Whisper Bot built with **Python 3.11+**, **`aiogram` v3**, **Telegram Bot API 10.0 Guest Mode**, and **Telegram Bot API Ephemeral Messages**.

---

## ✨ Features

- **Guest Mode (Bot API 10.0)**: Summon the bot in any group or private chat **without joining**! Simply mention the bot or reply to any message.
- **Inline Whispers (Any Chat)**: Send locked whisper cards anywhere across Telegram via `@psst_whisper_bot @recipient secret`.
- **Reply-to-Whisper**: Whisper to anyone by simply replying to their message—even if they don't have a Telegram username!
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

## ⚙️ @BotFather Configuration: Guest Mode vs. Inline Mode

> [!IMPORTANT]
> **Guest Mode and Inline Mode are Mutually Exclusive in Telegram Clients!**
> In Telegram clients, typing `@bot_name` in the chat input field behaves differently based on your bot's settings in [@BotFather](https://t.me/botfather):
> - **To use GUEST MODE**: **Inline Mode MUST be TURNED OFF**, and **Guest Mode MUST be ENABLED**.
>   When Inline Mode is disabled, Telegram allows users to type `@psst_whisper_bot secret` and press **Send** (or reply to any message) in chats where the bot is not a member. Telegram delivers these interactions via native `guest_message` updates!
> - **To use INLINE MODE**: **Inline Mode MUST be ENABLED**, and **Guest Mode MUST be DISABLED**.
>   When Inline Mode is active, typing `@psst_whisper_bot` immediately opens Telegram's inline query dropdown menu (`inline_query` updates), and Telegram **never** delivers `guest_message` updates.
> - A single bot token cannot run both simultaneously in the client because typing `@bot` either activates inline search OR sends a chat mention.

### Option 1: Configuring for Guest Mode (Recommended for Chats Without Adding Bot)
1. Message [@BotFather](https://t.me/botfather) and send `/mybots` -> Select your bot.
2. Go to **Bot Settings** -> **Inline Mode** -> Select **Turn Off** (or send `/setinline` and choose disable/turn off).
3. Under **Bot Settings** (or the BotFather Mini App), select **Guest Mode** -> toggle to **Enabled**.
4. *(Recommended)* Under **Bot Settings** -> **Group Privacy**, toggle privacy to **Turn off** so the bot can also read mentions when added to groups as a regular member.

### Option 2: Configuring for Inline Mode (Interactive Popup Cards)
1. Message [@BotFather](https://t.me/botfather) and send `/setinline`.
2. Select your bot and enter placeholder text (e.g. `Type: @recipient secret message`).
3. Under **Bot Settings**, ensure **Guest Mode** is toggled **Off**.

---

## 📖 Operational Modes

Psst! works across three distinct modes:

### 1. Guest Mode (`@psst_whisper_bot`) — No Joining Needed!
The bot participates in any group or private chat without being added as a member:
- **Reply to Any Message (Works for users with NO username):**
  Swipe right to reply to anyone's message and type:
  ```text
  @psst_whisper_bot secret message
  @psst_whisper_bot !1 secret message (self-destructs after reading)
  ```
- **Mention Recipients Directly:**
  ```text
  @psst_whisper_bot @bob meet me after work
  ```

### 2. Inline Query Mode (`@psst_whisper_bot`)
Works anywhere across Telegram by typing in the chat bar and selecting a card:
```text
@psst_whisper_bot @alice @bob The secret password is 1234
@psst_whisper_bot 12345678 87654321 Meeting at dusk
@psst_whisper_bot !1 @alice Self-destructing credentials
```

### 3. Group Command Mode (`/whisper`)
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
