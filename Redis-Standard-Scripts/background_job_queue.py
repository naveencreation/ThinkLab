"""Reliable background job queue with BRPOPLPUSH and acknowledgements."""

from __future__ import annotations

import argparse
import json
import time
import uuid

from redis_common import close_client, get_redis_client, validate_non_empty


PENDING_QUEUE = "jobs.pending"
PROCESSING_QUEUE = "jobs.processing"


def enqueue(job_type: str, payload: dict[str, str]) -> None:
    job_type = validate_non_empty(job_type, "job_type")

    job = {
        "id": str(uuid.uuid4()),
        "type": job_type,
        "payload": payload,
        "created_at": int(time.time()),
    }

    client = get_redis_client()
    try:
        client.lpush(PENDING_QUEUE, json.dumps(job))
        print(f"Enqueued job {job['id']}")
    finally:
        close_client(client)


def worker_loop() -> None:
    while True:
        client = None
        try:
            client = get_redis_client()
            print("Worker started")
            while True:
                raw = client.brpoplpush(PENDING_QUEUE, PROCESSING_QUEUE, timeout=5)
                if raw is None:
                    continue

                job = json.loads(raw)
                print(f"Processing job {job['id']} type={job['type']}")
                time.sleep(1)

                client.lrem(PROCESSING_QUEUE, 1, raw)
                print(f"Acked job {job['id']}")
        except Exception as exc:
            print(f"Worker error: {exc}. reconnecting in 2s...")
            time.sleep(2)
        finally:
            if client:
                close_client(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redis background queue example")
    parser.add_argument("mode", choices=["enqueue", "worker"])
    parser.add_argument("--type", default="send_email")
    parser.add_argument("--payload", default='{"to":"user@example.com"}')
    args = parser.parse_args()

    if args.mode == "enqueue":
        enqueue(args.type, json.loads(args.payload))
    else:
        worker_loop()
