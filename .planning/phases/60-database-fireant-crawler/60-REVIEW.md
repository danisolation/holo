---
phase: 60-database-fireant-crawler
reviewed: 2026-05-05T15:16:40Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - backend/app/models/rumor.py
  - backend/alembic/versions/028_create_rumors_table.py
  - backend/app/crawlers/fireant_crawler.py
  - backend/app/crawlers/types.py
  - backend/app/config.py
  - backend/app/resilience.py
  - backend/tests/test_fireant_crawler.py
findings:
  critical: 0
  warning: 4
  info: 2
  total: 6
status: issues_found
---

# Phase 60: Code Review Report

**Reviewed:** 2026-05-05T15:16:40Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

The FireantCrawler implementation is well-structured and closely mirrors the established CafeFCrawler pattern — good consistency. The Rumor model, migration, TypedDict, config, circuit breaker, and tests are all properly wired. No security vulnerabilities found (token comes from env, no injection vectors, no user-controlled input reaches SQL).

Key concerns are around resilience: a single malformed post in the API response kills the entire ticker's crawl, the API response shape isn't validated, and an empty token config silently produces failing requests. These are all fixable with small guards.

## Warnings

### WR-01: KeyError on missing `postID` or `date` crashes entire ticker crawl

**File:** `backend/app/crawlers/fireant_crawler.py:170-178`
**Issue:** `post["postID"]` (line 170) and `post["date"]` (line 178) use direct dict access without `.get()`. If the Fireant API returns a post missing either field, `KeyError` propagates up through `_parse_posts` → `_fetch_posts_raw` → `_fetch_posts` → `crawl_watchlist_tickers`, where the outer `except` catches it — but this means **all posts for that ticker are lost**, not just the malformed one. Other fields correctly use `.get()` with defaults.
**Fix:** Wrap individual post parsing in try/except within the loop:
```python
for post in posts_json:
    try:
        content = html.unescape(post.get("content", "")).strip()
        if len(content) < self.MIN_CONTENT_LENGTH:
            continue

        parsed.append({
            "post_id": post["postID"],
            "content": content,
            "author_name": post.get("user", {}).get("name", "Unknown"),
            "is_authentic": post.get("user", {}).get("isAuthentic", False),
            "total_likes": post.get("totalLikes", 0),
            "total_replies": post.get("totalReplies", 0),
            "fireant_sentiment": post.get("sentiment", 0),
            "posted_at": datetime.fromisoformat(post["date"]),
        })
    except (KeyError, ValueError) as e:
        logger.debug(f"Skipping malformed Fireant post: {e}")
        continue
```

### WR-02: No validation that API response is a list

**File:** `backend/app/crawlers/fireant_crawler.py:157`
**Issue:** `_parse_posts` assumes `posts_json` is a `list[dict]`. If the Fireant API returns an error object (e.g. `{"error": "rate limited"}`) instead of an array, iterating over a dict yields its keys as strings, and `post.get("content", "")` etc. will fail with `AttributeError` on a string. This would bubble up and fail the ticker.
**Fix:** Add a type guard at the start of `_parse_posts`:
```python
def _parse_posts(self, posts_json: list[dict]) -> list[dict]:
    if not isinstance(posts_json, list):
        logger.warning(f"Fireant API returned non-list response: {type(posts_json)}")
        return []
    # ... rest of method
```

### WR-03: Empty `fireant_token` produces silent 401 failures

**File:** `backend/app/config.py:69` / `backend/app/crawlers/fireant_crawler.py:51`
**Issue:** `fireant_token` defaults to `""`. When empty, the crawler sends `Authorization: Bearer ` (empty token) which will 401 on every request. All tickers fail, circuit breaker opens, but the root cause (missing config) isn't obvious from the logs — it just shows `HTTPStatusError` 401 for each ticker.
**Fix:** Add an early check in `crawl_watchlist_tickers`:
```python
if not settings.fireant_token:
    logger.warning("Fireant crawl skipped: fireant_token not configured")
    return {"success": 0, "failed": 0, "total_posts": 0, "failed_symbols": []}
```

### WR-04: Model Python defaults vs migration server defaults mismatch

**File:** `backend/app/models/rumor.py:29-32` / `backend/alembic/versions/028_create_rumors_table.py:25-28`
**Issue:** The Rumor model defines `default=False` / `default=0` (Python-side ORM defaults) for `is_authentic`, `total_likes`, `total_replies`, `fireant_sentiment`. But the migration defines `server_default=sa.text("false")` / `server_default=sa.text("0")` (PostgreSQL-side defaults). These are two different default mechanisms. The current crawler always provides explicit values so neither default is used today, but if someone later creates a `Rumor()` via ORM without setting these fields, the Python default applies but no `DEFAULT` clause appears in the INSERT SQL. Conversely, raw SQL inserts get the server default but not the Python one. The NewsArticle model (reference pattern) doesn't have this issue because it only uses `server_default` for `created_at`.
**Fix:** Use `server_default` in the model to match the migration, or use both:
```python
is_authentic: Mapped[bool] = mapped_column(
    Boolean, server_default=text("false"), default=False
)
total_likes: Mapped[int] = mapped_column(
    Integer, server_default=text("0"), default=0
)
# ... same for total_replies, fireant_sentiment
```

## Info

### IN-01: Test coverage gap — no test for malformed API responses

**File:** `backend/tests/test_fireant_crawler.py`
**Issue:** Tests cover happy path parsing, short content filtering, missing user field, and empty input — but no test for: (1) missing `postID` field, (2) missing `date` field, (3) non-list API response (dict/error object), (4) invalid date format. These are the exact edge cases flagged in WR-01 and WR-02.
**Fix:** Add test cases:
```python
def test_parse_posts_missing_post_id_skips(self):
    """Post missing postID should be skipped, not crash."""
    crawler = _make_crawler()
    posts = [{"content": "x" * 25, "date": "2025-07-21T10:00:00+07:00", ...}]  # no postID
    result = crawler._parse_posts(posts)
    assert len(result) == 0

def test_parse_posts_non_list_returns_empty(self):
    """Non-list API response should return empty list."""
    crawler = _make_crawler()
    assert crawler._parse_posts({"error": "rate limited"}) == []
```

### IN-02: `_is_retryable` doesn't handle 429 (Too Many Requests) distinctly

**File:** `backend/app/crawlers/fireant_crawler.py:30-35`
**Issue:** HTTP 429 (rate limit) falls through to `return False` since `429 < 500`. Rate-limited requests won't be retried, which may be fine (the circuit breaker will handle sustained failures), but it's worth noting since the 1.5s delay between tickers is specifically for rate limiting. If Fireant returns 429, a retry with backoff would be more appropriate than immediate failure.
**Fix:** Consider adding 429 to retryable statuses:
```python
if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (429, *range(500, 600)):
    return True
```

---

_Reviewed: 2026-05-05T15:16:40Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_
