"""Session storage with secure token IDs and TTL refresh."""

from __future__ import annotations

import json
import secrets
import time

from redis_common import close_client, get_redis_client


SESSION_TTL_SECONDS = 1800


def create_session(client, user_id: str, roles: list[str]) -> str:
    token = secrets.token_urlsafe(32)
    session_key = f"session:{token}"
    payload = {
        "user_id": user_id,
        "roles": roles,
        "created_at": int(time.time()),
    }
    client.setex(session_key, SESSION_TTL_SECONDS, json.dumps(payload))
    return token


def get_session(client, token: str) -> dict | None:
    raw = client.get(f"session:{token}")
    if not raw:
        return None
    client.expire(f"session:{token}", SESSION_TTL_SECONDS)
    return json.loads(raw)


def invalidate_session(client, token: str) -> None:
    client.delete(f"session:{token}")


def main() -> None:
    client = get_redis_client()
    try:
        token = create_session(client, "user-1001", ["admin", "billing"])
        print(f"created token={token[:10]}... (truncated)")

        session = get_session(client, token)
        print("loaded session:", session)

        invalidate_session(client, token)
        print("session invalidated")
    finally:
        close_client(client)


if __name__ == "__main__":
    main()
