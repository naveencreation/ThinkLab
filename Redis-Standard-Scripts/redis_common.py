"""Shared Redis helpers with retry, TLS, and input validation."""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from typing import Any, Callable, TypeVar

from dotenv import load_dotenv
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError, TimeoutError

load_dotenv()

T = TypeVar("T")


@dataclass(frozen=True)
class RedisSettings:
    host: str = os.getenv("REDIS_HOST", "127.0.0.1")
    port: int = int(os.getenv("REDIS_PORT", "6379"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    username: str | None = os.getenv("REDIS_USERNAME") or None
    password: str | None = os.getenv("REDIS_PASSWORD") or None
    use_tls: bool = os.getenv("REDIS_USE_TLS", "false").lower() == "true"
    tls_ca_cert: str | None = os.getenv("REDIS_TLS_CA_CERT") or None
    tls_client_cert: str | None = os.getenv("REDIS_TLS_CLIENT_CERT") or None
    tls_client_key: str | None = os.getenv("REDIS_TLS_CLIENT_KEY") or None
    socket_timeout: float = float(os.getenv("REDIS_SOCKET_TIMEOUT", "3"))
    connect_timeout: float = float(os.getenv("REDIS_CONNECT_TIMEOUT", "3"))
    retry_attempts: int = int(os.getenv("REDIS_RETRY_ATTEMPTS", "5"))
    retry_base_delay: float = float(os.getenv("REDIS_RETRY_BASE_DELAY", "0.25"))


def get_redis_client(settings: RedisSettings | None = None) -> Redis:
    cfg = settings or RedisSettings()

    if cfg.password is None:
        raise ValueError("REDIS_PASSWORD must be set for production-safe AUTH.")

    kwargs: dict[str, Any] = {
        "host": cfg.host,
        "port": cfg.port,
        "db": cfg.db,
        "username": cfg.username,
        "password": cfg.password,
        "socket_timeout": cfg.socket_timeout,
        "socket_connect_timeout": cfg.connect_timeout,
        "health_check_interval": 30,
        "retry_on_timeout": True,
        "decode_responses": True,
    }

    if cfg.use_tls:
        kwargs["ssl"] = True
        if cfg.tls_ca_cert:
            kwargs["ssl_ca_certs"] = cfg.tls_ca_cert
        if cfg.tls_client_cert:
            kwargs["ssl_certfile"] = cfg.tls_client_cert
        if cfg.tls_client_key:
            kwargs["ssl_keyfile"] = cfg.tls_client_key

    client = Redis(**kwargs)
    client.ping()
    return client


def execute_with_retry(operation: Callable[[], T], settings: RedisSettings | None = None) -> T:
    cfg = settings or RedisSettings()
    last_error: Exception | None = None

    for attempt in range(1, cfg.retry_attempts + 1):
        try:
            return operation()
        except (RedisConnectionError, TimeoutError) as exc:
            last_error = exc
            jitter = random.uniform(0, cfg.retry_base_delay)
            backoff = (cfg.retry_base_delay * (2 ** (attempt - 1))) + jitter
            print(f"Retryable Redis error (attempt={attempt}): {exc}")
            time.sleep(backoff)

    raise RuntimeError(f"Redis operation failed after {cfg.retry_attempts} attempts") from last_error


def validate_non_empty(value: str, field_name: str, max_len: int = 256) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{field_name} cannot be empty")
    if len(text) > max_len:
        raise ValueError(f"{field_name} exceeds max length {max_len}")
    return text


def close_client(client: Redis) -> None:
    try:
        client.close()
    except RedisError:
        pass
