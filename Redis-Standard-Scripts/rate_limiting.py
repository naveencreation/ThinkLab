"""Sliding-window rate limiting using sorted sets."""

from __future__ import annotations

import time

from redis_common import close_client, get_redis_client, validate_non_empty


def allow_request(client, subject: str, limit: int, window_seconds: int) -> bool:
    subject = validate_non_empty(subject, "subject")
    now_ms = int(time.time() * 1000)
    window_start_ms = now_ms - (window_seconds * 1000)
    key = f"ratelimit:{subject}"

    pipe = client.pipeline()
    pipe.zremrangebyscore(key, 0, window_start_ms)
    pipe.zadd(key, {str(now_ms): now_ms})
    pipe.zcard(key)
    pipe.expire(key, window_seconds)
    _, _, request_count, _ = pipe.execute()
    return int(request_count) <= limit


def main() -> None:
    client = get_redis_client()
    try:
        subject = "user:42"
        for i in range(1, 9):
            allowed = allow_request(client, subject, limit=5, window_seconds=10)
            print(f"request={i} allowed={allowed}")
            time.sleep(0.6)
    finally:
        close_client(client)


if __name__ == "__main__":
    main()
