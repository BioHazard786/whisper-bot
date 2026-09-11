# AGENTS.md: Developer & Agent Reference Guide for Psst! Whisper Bot

Welcome to **Psst!**, a high-performance, privacy-focused Telegram Whisper Bot built using **`aiogram` v3**, **Telegram Bot API Ephemeral Messages and Commands**, and modern **Python 3.11+ / asyncio**.

---

## 1. Overview & Architecture

Psst! enables Telegram users to send confidential, target-restricted, and self-destructing messages across two operational modes:

1. **Inline Query Mode (`@psst_whisper_bot`)**: Works anywhere across Telegram (private chats, groups, channels) by generating locked cards via Telegram's inline dropdown.
2. **Group Chat Ephemeral Mode (`/whisper`, `/psst`)**: Uses native Telegram Bot API **Ephemeral Commands** and **Ephemeral Messages** directly inside group chats where the bot is a member.

### High-Level Architecture Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                         Telegram Client (User)                         │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
     (Inline Mode: @bot @user text)       (Group Command: /whisper)
                    │                                │
                    ▼                                ▼
       ┌─────────────────────────┐      ┌────────────────────────────┐
       │      inline_router      │      │        group_router        │
       │ (Parses & saves whisper │      │ (Ephemeral command intake, │
       │  generates locked cards)│      │  posts locked group prompt)│
       └────────────┬────────────┘      └────────────┬───────────────┘
                    │                                │
                    └────────────────┬───────────────┘
                                     ▼
                     ┌───────────────────────────────┐
                     │       callbacks_router        │
                     │  [ 🔒 Open ] / [ 🗑️ Delete ]   │
                     └───────────────┬───────────────┘
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
         Group Message Context?            Inline Message Context?
                     │                               │
         ┌───────────┴────────────┐                  ▼
         │ Ephemeral Message API: │       answerCallbackQuery
         │ send_message with      │       (show_alert=True)
         │ ephemeral_parameters   │       Private modal popup
         └────────────────────────┘
```

---

## 2. Deep Dive: Telegram Bot API Ephemeral Features

### A. Ephemeral Commands (`is_ephemeral=True`)
- Registered via `bot.set_my_commands` using `BotCommandScopeAllGroupChats()`:
  ```python
  BotCommand(
      command="whisper",
      description="Send a private whisper to someone in this chat",
      is_ephemeral=True,
  )
  ```
- **Behavior**: On modern Telegram clients, when a user types `/whisper @recipient message`, Telegram hides the command text from everyone else in the group. The bot deletes the command message upon receipt as an extra safeguard for legacy clients.

### B. Ephemeral Message Delivery (`ephemeral_message_parameters`)
- Supported in group chats when responding to an active callback query within 15 seconds:
  ```python
  from aiogram.types import EphemeralMessageParameters, ReplyParameters

  await bot.send_message(
      chat_id=callback.message.chat.id,
      text=f"🤫 **Whisper:**\n\n{secret_text}",
      ephemeral_message_parameters=EphemeralMessageParameters(
          receiver_user_id=callback.from_user.id,
          callback_query_id=callback.id,
      ),
      reply_parameters=ReplyParameters(message_id=callback.message.message_id),
  )
  ```
- **Behavior**: The whisper renders on the recipient's chat timeline **only**. Other group members cannot see this message.
- **Key Advantage (Long Whispers)**: Because ephemeral messages are delivered directly onto the recipient's chat timeline via `bot.send_message`, they support **full Telegram message lengths up to 4,096 characters** and rich text formatting (bold, code blocks, lists). This completely eliminates the character truncation issue of modal alert popups!

### C. Inline Query Fallback
- Telegram inline messages do not expose a group `chat_id` inside callback queries for privacy reasons (`callback.inline_message_id` is set, `callback.message` is `None`).
- The bot gracefully handles inline messages using `answerCallbackQuery(text=..., show_alert=True)`, rendering a secure modal popup on all devices.
- **Dialog Box Limitation**: Telegram's `show_alert=True` popup modal is restricted to short text (approx. 200 characters) before truncation. For long confidential documents, logs, or multi-paragraph notes, users should use Group Command Mode (`/whisper`).

---

## 3. Project Structure

```
whisper-bot/
├── .env                              # Environment variables (BOT_TOKEN, LOG_LEVEL, etc.)
├── AGENTS.md                         # This reference guide
├── pyproject.toml                    # UV build config, ruff, pyright, pytest settings
├── uv.lock                           # Locked dependency tree
├── src/
│   └── whisper_bot/
│       ├── __init__.py               # Package root (exports main)
│       ├── main.py                   # App lifecycle, command setup, and polling loop
│       ├── config.py                 # Pydantic Settings singleton (get_settings)
│       ├── logger.py                 # Structlog setup (JSON in prod, Console in dev)
│       ├── models/
│       │   ├── __init__.py
│       │   └── whisper.py            # Whisper model, WhisperStatus, can_view logic
│       ├── services/
│       │   ├── __init__.py
│       │   ├── storage.py            # WhisperStorageProtocol & MemoryWhisperStorage
│       │   └── whisper_service.py    # Creation, authorization, one-time read, cleanup
│       ├── middlewares/
│       │   ├── __init__.py
│       │   ├── logging.py            # Structlog request tracing & execution timing
│       │   └── throttling.py         # Anti-spam cooldown per user
│       ├── handlers/
│       │   ├── __init__.py
│       │   ├── common.py             # /start, /help, /stats, /ping & menu callbacks
│       │   ├── inline.py             # Inline queries & chosen inline result tracking
│       │   ├── callbacks.py          # Callback queries for opening/deleting whispers
│       │   └── group.py              # Group commands (/whisper, /psst)
│       └── utils/
│           ├── __init__.py
│           └── query_parser.py       # Query parser for @targets, IDs, and flags
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Pytest fixtures
    ├── test_handlers.py              # Handler mock tests
    ├── test_parser.py                # Query parser unit tests
    ├── test_storage.py               # Memory storage & TTL eviction tests
    └── test_whisper_service.py       # Authorization & one-time destruction tests
```

---

## 4. Development & Maintenance Commands

All commands are managed through `uv`:

### Running the Bot
```bash
# Via console script entry point
uv run whisper-bot

# Or via Python module
uv run python -m whisper_bot.main
```

### Code Formatting & Linting (`ruff`)
```bash
# Check code style and lint rules
uv run ruff check .

# Automatically apply fixes
uv run ruff check --fix .

# Check code formatting
uv run ruff format --check .

# Auto-format files
uv run ruff format .
```

### Static Type Checking (`pyright`)
```bash
uv run pyright
```

### Running Tests (`pytest`)
```bash
uv run pytest -v
```

---

### Docker Deployment
```bash
# Build and run with Docker Compose
docker compose up -d

# View real-time logs
docker compose logs -f

# Stop containers
docker compose down
```

---

## 5. Configuration Reference

Environment variables supported via `.env` (managed by `pydantic-settings` in `whisper_bot/config.py`):

| Variable | Type | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | `str` | *Required* | Telegram Bot API token from `@BotFather` |
| `LOG_LEVEL` | `str` | `"INFO"` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `APP_ENV` | `str` | `"development"` | `"development"` (Console logs) or `"production"` (JSON logs) |
| `DEFAULT_WHISPER_TTL_SECONDS` | `int` | `86400` (24h) | Time after which unread whispers auto-expire |
| `CLEANUP_INTERVAL_SECONDS` | `int` | `300` (5m) | Background sweep frequency for purging expired whispers |
| `RATE_LIMIT_SECONDS` | `float` | `0.3` | Minimum cooldown between user callback clicks |
| `STORAGE_BACKEND` | `str` | `"sqlite"` | Storage backend: `"sqlite"` (dual in-memory + SQLite) or `"memory"` |
| `SQLITE_DB_PATH` | `str` | `"data/whispers.db"` | File path for SQLite database |
| `LOG_CHANNEL` | `int \| str` | `None` | Optional Telegram channel ID or `@username` for audit logging whispers |

---

## 6. Extending the Codebase

### Storage Layer Architecture
Psst! uses a dual storage architecture by default (`SqliteWhisperStorage`):
- **L1 In-Memory Cache**: Fast in-memory dictionary cache for sub-millisecond retrieval and instant button unlocks.
- **L2 SQLite Persistence**: Asynchronous WAL-mode SQLite database powered by `aiosqlite` ensuring zero data loss across restarts or container redeployments.

To implement another backend (e.g., Redis for multi-node clustering), implement the `WhisperStorageProtocol` in `src/whisper_bot/services/storage.py`:
```python
class RedisWhisperStorage:
    async def save(self, whisper: Whisper) -> None: ...
    async def get(self, whisper_id: str) -> Whisper | None: ...
    async def update(self, whisper: Whisper) -> None: ...
    async def delete(self, whisper_id: str) -> bool: ...
    async def cleanup_expired(self) -> int: ...
    async def get_stats(self) -> dict[str, int]: ...
```
Then inject the new storage instance in `src/whisper_bot/main.py`.
