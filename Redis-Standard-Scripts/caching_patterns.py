"""Caching patterns: key-value, TTL, cache-aside, write-through."""

from __future__ import annotations

import json
import time

from redis_common import close_client, execute_with_retry, get_redis_client, validate_non_empty


# Simulated DB
DB: dict[str, dict[str, str]] = {
    "user:1001": {"name": "Asha", "plan": "pro"},
    "user:1002": {"name": "Noah", "plan": "free"},
}


def db_read(key: str) -> dict[str, str] | None:
    time.sleep(0.05)
    return DB.get(key)


def db_write(key: str, value: dict[str, str]) -> None:
    time.sleep(0.05)
    DB[key] = value


def cache_aside_get(client, key: str, ttl_seconds: int = 60) -> dict[str, str] | None:
    key = validate_non_empty(key, "key")
    cached = execute_with_retry(lambda: client.get(key))
    if cached:
        return json.loads(cached)

    record = db_read(key)
    if record is None:
        return None

    execute_with_retry(lambda: client.setex(key, ttl_seconds, json.dumps(record)))
    return record


def write_through_set(client, key: str, value: dict[str, str], ttl_seconds: int = 60) -> None:
    key = validate_non_empty(key, "key")
    db_write(key, value)
    payload = json.dumps(value)
    execute_with_retry(lambda: client.setex(key, ttl_seconds, payload))


def main() -> None:
    client = get_redis_client()
    try:
        execute_with_retry(lambda: client.set("app:status", "healthy"))
        execute_with_retry(lambda: client.setex("app:ttl-demo", 10, "expires soon"))

        print("Basic key-value:", execute_with_retry(lambda: client.get("app:status")))
        print("TTL remaining:", execute_with_retry(lambda: client.ttl("app:ttl-demo")))

        print("Cache-aside miss -> DB -> cache:", cache_aside_get(client, "user:1001"))
        print("Cache-aside hit:", cache_aside_get(client, "user:1001"))

        write_through_set(client, "user:1003", {"name": "Mia", "plan": "team"}, ttl_seconds=120)
        print("Write-through read:", cache_aside_get(client, "user:1003"))
    finally:
        close_client(client)


if __name__ == "__main__":
    main()
