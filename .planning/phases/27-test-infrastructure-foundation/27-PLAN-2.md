---
phase: 27
plan: 2
type: backend
wave: 1
depends_on: []
files_modified:
  - backend/app/main.py
  - backend/app/config.py
autonomous: true
requirements: [INFRA-02]
---

# Plan 27.2: HOLO_TEST_MODE Environment Guard

<objective>
Add HOLO_TEST_MODE setting to backend config and guard APScheduler + Telegram bot startup in lifespan, so test runs don't trigger scheduled jobs or bot connections.
</objective>

<tasks>

<task id="1" type="file">
<title>Add holo_test_mode setting to Settings class</title>
<read_first>
- backend/app/config.py (current Settings class, all fields)
</read_first>
<action>
Add a new field to the `Settings` class in `backend/app/config.py`, after the existing fields (before `settings = Settings()`):

```python
    # Test Mode (Phase 27 — E2E testing)
    holo_test_mode: bool = False  # Set True to skip scheduler + telegram in tests
```

This field reads from HOLO_TEST_MODE env var via pydantic-settings. Default is False so normal operation is unaffected.
</action>
<verify>
`backend/app/config.py` contains `holo_test_mode: bool = False`
</verify>
<acceptance_criteria>
- `backend/app/config.py` contains `holo_test_mode: bool = False`
- Field is inside the `Settings` class (indented under `class Settings`)
</acceptance_criteria>
</task>

<task id="2" type="file">
<title>Guard scheduler and telegram startup with test mode check</title>
<read_first>
- backend/app/main.py (lifespan function — lines 20-41)
- backend/app/config.py (settings import pattern)
</read_first>
<action>
Modify the `lifespan` function in `backend/app/main.py` to conditionally skip scheduler and telegram bot when test mode is active.

Add import at top of file:
```python
from app.config import settings
```

Replace the current lifespan startup block:
```python
    # Startup
    logger.info("Holo starting up...")
    configure_jobs()
    scheduler.start()
    logger.info("Scheduler started with configured jobs")
    try:
        await telegram_bot.start()
    except Exception as e:
        logger.warning(f"Telegram bot failed to start (continuing without it): {e}")
```

With:
```python
    # Startup
    logger.info("Holo starting up...")
    if settings.holo_test_mode:
        logger.info("HOLO_TEST_MODE=true — skipping scheduler and Telegram bot")
    else:
        configure_jobs()
        scheduler.start()
        logger.info("Scheduler started with configured jobs")
        try:
            await telegram_bot.start()
        except Exception as e:
            logger.warning(f"Telegram bot failed to start (continuing without it): {e}")
```

Also update the shutdown block to only stop what was started:
```python
    # Shutdown
    if not settings.holo_test_mode:
        try:
            await telegram_bot.stop()
        except Exception:
            pass
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
    await engine.dispose()
    logger.info("Database engine disposed. Holo shut down.")
```
</action>
<verify>
`backend/app/main.py` contains `if settings.holo_test_mode:` and `skipping scheduler and Telegram bot`
</verify>
<acceptance_criteria>
- `backend/app/main.py` contains `from app.config import settings`
- `backend/app/main.py` contains `if settings.holo_test_mode:`
- `backend/app/main.py` contains `skipping scheduler and Telegram bot`
- `backend/app/main.py` contains `if not settings.holo_test_mode:` in shutdown block
- Scheduler `configure_jobs()` and `scheduler.start()` are inside `else` block
- `telegram_bot.start()` is inside `else` block
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `backend/app/config.py` has `holo_test_mode: bool = False` in Settings
2. `backend/app/main.py` lifespan guards scheduler+telegram behind `if not settings.holo_test_mode`
3. Existing backend tests still pass (holo_test_mode defaults to False)
</verification>

<success_criteria>
Addresses INFRA-02: HOLO_TEST_MODE=true prevents APScheduler jobs and Telegram bot from starting during test runs.
</success_criteria>

<must_haves>
- holo_test_mode bool setting in config (default False)
- Scheduler start guarded by test mode check
- Telegram bot start guarded by test mode check
- Shutdown block also guarded (don't stop what wasn't started)
</must_haves>
