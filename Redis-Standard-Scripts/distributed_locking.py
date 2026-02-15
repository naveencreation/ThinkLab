"""Distributed lock example using Redis lock primitive."""

from __future__ import annotations

import argparse
import time

from redis_common import close_client, get_redis_client, validate_non_empty


def run_critical_section(lock_name: str, worker_name: str, ttl: int = 10) -> None:
    lock_name = validate_non_empty(lock_name, "lock_name")
    worker_name = validate_non_empty(worker_name, "worker_name")

    client = get_redis_client()
    lock = client.lock(name=lock_name, timeout=ttl, blocking_timeout=3, thread_local=False)

    try:
        acquired = lock.acquire(blocking=True)
        if not acquired:
            print(f"[{worker_name}] lock busy")
            return

        print(f"[{worker_name}] acquired lock '{lock_name}'")
        time.sleep(2)
        print(f"[{worker_name}] completed protected work")
    finally:
        if lock.owned():
            lock.release()
            print(f"[{worker_name}] released lock")
        close_client(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redis distributed lock example")
    parser.add_argument("--lock", default="locks.inventory-update")
    parser.add_argument("--worker", default="worker-1")
    parser.add_argument("--ttl", type=int, default=10)
    args = parser.parse_args()

    run_critical_section(args.lock, args.worker, args.ttl)
