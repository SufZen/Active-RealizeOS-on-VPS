> **Internal/historical document — not user-facing operator documentation. See root `CLAUDE.md` and `setup-guide.md` for current operating guidance.**

# Channels & Communication Optimization — Design Spec

## Problem

The channel layer has 14 issues across correctness, reliability, security, and consistency. The most impactful: the humanizer is never called from Telegram (primary channel), the humanizer import in `chat.py` references a non-existent function name, Telegram hard-splits messages without respecting word boundaries, and webhooks lack replay protection and rate limiting.

## Scope

### IN
- `realize_core/channels/base.py` — humanizer integration in `handle_incoming()`
- `realize_core/channels/telegram.py` — message splitting, markdown escaping, error recovery, super_agent fixes
- `realize_core/channels/webhooks.py` — replay protection, rate limiting
- `realize_core/channels/scheduler.py` — failure tracking, status improvement
- `realize_core/utils/humanizer.py` — fix function name, remove truncation, add channel variants
- NEW: `realize_core/utils/message_utils.py` — shared message splitting, Telegram markdown escaping
- `realize_api/routes/chat.py` — remove duplicate humanizer call
- NEW: `tests/test_channels.py` — comprehensive channel tests

### OUT
- `realize_core/channels/whatsapp.py` — skip entirely
- `realize_core/channels/web.py` — no changes (no streaming, humanizer auto-applied via base)
- Engine-level changes (no `process_message` pipeline changes)
- Timezone-aware scheduling

## Design

### 1. Humanizer Integration (P0)

**Root cause:** Humanization is opt-in per call site, and the API route uses the wrong function name.

**Fix:**

a) In `humanizer.py`: add `clean_output` as the primary function name (rename `humanize` to `clean_output`, keep `humanize` as alias for backward compat).

b) Remove the `_clean_for_telegram` truncation (line 79-80). Message length is the channel's job, not the humanizer's. The humanizer should only strip AI artifacts.

c) Add `_clean_for_whatsapp` (strip headers, code blocks — same as telegram) and `_clean_for_web` (no-op, markdown is fine).

d) In `base.py`: add to `BaseChannel`:
```python
humanize_output: bool = True  # class attribute
```
In `handle_incoming()`, after getting response text, call `clean_output(response_text, channel=self.channel_name)` if `humanize_output` is True.

e) In `webhooks.py`: set `humanize_output = False` in `WebhookChannel.__init__()`.

f) In `chat.py`: remove the try/except block at lines 72-77 that calls `clean_output` — it's now handled by the base channel.

### 2. Telegram Reliability (P1)

**2a. Smart Message Splitting**

Extract WhatsApp's `_split_message()` into `realize_core/utils/message_utils.py` as a shared utility. The function splits on newline boundaries first, then word boundaries, then hard-splits. Signature:
```python
def split_message(text: str, max_len: int = 4096) -> list[str]
```

Update Telegram's `send_message()` and `_send_response()` to use this utility. Remove WhatsApp's local copy and import from the shared location.

**2b. ~~Telegram Markdown Escaping~~ — REMOVED**

Not needed. The bot sends without `parse_mode`, so Telegram treats all messages as plain text. No special characters can break formatting. If `parse_mode` is added in the future, escaping will be needed then.

**2c. Error Recovery on Send**

Wrap the send call in `_send_response()` with:
```python
try:
    await update.message.reply_text(chunk)
except Exception as e:
    logger.error(f"Telegram send failed: {e}")
    try:
        # Retry once for transient errors
        await asyncio.sleep(1)
        await update.message.reply_text(chunk)
    except Exception:
        logger.error(f"Telegram send retry failed for user {update.message.from_user.id}")
```

Apply the same pattern to `send_message()`.

**2d. Consolidate Send Methods**

`send_message()` should use the same `split_message()` utility. Currently it hard-splits at 4096.

**2e. Super_agent Mode Fix**

In `/brief`, `/done`, `/reset`: when `self.mode == "super_agent"`, resolve system_key via `_resolve_system_key()` before calling `clear_history()`. Currently they always use `self.system_key` which is empty in super_agent mode, clearing the wrong history.

### 3. Webhook Security (P2)

**3a. Replay Protection**

Add to `WebhookEndpoint`:
```python
replay_protection: bool = False
max_age_seconds: int = 300  # 5 minutes
timestamp_field: str = "timestamp"  # payload field containing Unix timestamp
```

In `process_webhook()`, if `endpoint.replay_protection` is True:
- Extract timestamp from payload using `endpoint.timestamp_field`
- Reject if `time.time() - timestamp > endpoint.max_age_seconds`
- Log warning on rejection

Configurable in YAML:
```yaml
webhooks:
  github_push:
    replay_protection: true
    max_age_seconds: 300
```

**3b. Rate Limiting**

Add a simple token bucket rate limiter to `WebhookChannel`:
```python
_rate_counters: dict[str, list[float]]  # endpoint_name → list of timestamps
```

In `process_webhook()`, before processing:
- Check if requests in last 60 seconds exceed limit (default: 60/min)
- Configurable per-endpoint via `rate_limit` field
- Return `None` with warning log when exceeded

### 4. Scheduler Robustness (P2)

Add to `ScheduledJob`:
```python
consecutive_failures: int = 0
last_error: str = ""
max_failures: int = 5  # auto-disable after this many consecutive failures
```

In `_execute_job()`:
- On success: reset `consecutive_failures` to 0, clear `last_error`
- On failure: increment `consecutive_failures`, store error string in `last_error`
- If `consecutive_failures >= max_failures`: set `job.enabled = False`, log warning

Update `status_summary()` to include `consecutive_failures` and `last_error`.

### 5. Shared Utilities (P3)

**New file: `realize_core/utils/message_utils.py`**

Contains:
- `split_message(text, max_len=4096)` — smart splitting (newline > space > hard)

This file is imported by `telegram.py`. WhatsApp's local `_split_message()` can be updated to import from here in a future WhatsApp optimization.

### 6. Tests

**New file: `tests/test_channels.py`**

Test categories:
- `test_split_message_*` — boundary cases, Unicode, empty, exact-length, no-space lines
- `test_humanizer_*` — clean_output called, webhook opt-out, channel-specific cleaning
- `test_webhook_replay_protection` — old payloads rejected, valid payloads accepted
- `test_webhook_rate_limiting` — excess requests rejected, normal flow passes
- `test_scheduler_failure_tracking` — auto-disable after N failures, reset on success
- `test_super_agent_command_routing` — /brief, /done, /reset resolve correct system_key

## Priority Order

| # | Issue | Priority | File(s) |
|---|-------|----------|---------|
| 1 | Fix `clean_output` name mismatch | P0 | humanizer.py, chat.py |
| 2 | Integrate humanizer in BaseChannel | P0 | base.py, webhooks.py |
| 3 | Smart message splitting (shared util) | P1 | message_utils.py (new), telegram.py |
| 4 | Telegram error recovery | P1 | telegram.py |
| 5 | Super_agent mode command fixes | P1 | telegram.py |
| 6 | Remove humanizer truncation conflict | P2 | humanizer.py |
| 7 | Webhook replay protection | P2 | webhooks.py |
| 8 | Webhook rate limiting | P2 | webhooks.py |
| 9 | Scheduler failure tracking | P2 | scheduler.py |
| 10 | Consolidate Telegram send methods | P3 | telegram.py |
| 11 | Add missing humanizer channel variants | P3 | humanizer.py |
| 12 | Scheduler status improvement | P4 | scheduler.py |
| 13 | Channel tests | ALL | test_channels.py (new) |

## Verification

1. `python -m pytest tests/test_channels.py -v` — all new tests pass
2. `python -m pytest tests/ -q` — full suite passes, no regressions
3. `python -m ruff check realize_core/channels/ realize_core/utils/humanizer.py realize_core/utils/message_utils.py` — lint clean
4. Manual: `python cli.py status` — verify channel status reporting works
