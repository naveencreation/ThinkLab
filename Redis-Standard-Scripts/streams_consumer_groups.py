"""Redis Streams with consumer groups and explicit acknowledgements."""

from __future__ import annotations

import argparse
import time

from redis.exceptions import ResponseError

from redis_common import close_client, execute_with_retry, get_redis_client, validate_non_empty


STREAM_KEY = "stream.orders"
GROUP_NAME = "order-processors"


def ensure_group(client) -> None:
    try:
        client.xgroup_create(name=STREAM_KEY, groupname=GROUP_NAME, id="0", mkstream=True)
        print("Consumer group created")
    except ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


def produce(order_id: str, customer_id: str) -> None:
    order_id = validate_non_empty(order_id, "order_id")
    customer_id = validate_non_empty(customer_id, "customer_id")

    client = get_redis_client()
    try:
        ensure_group(client)
        event_id = execute_with_retry(
            lambda: client.xadd(STREAM_KEY, {"order_id": order_id, "customer_id": customer_id}, maxlen=100_000, approximate=True)
        )
        print(f"Produced event_id={event_id}")
    finally:
        close_client(client)


def consume(consumer_name: str) -> None:
    consumer_name = validate_non_empty(consumer_name, "consumer_name")

    while True:
        client = None
        try:
            client = get_redis_client()
            ensure_group(client)
            print(f"Consumer '{consumer_name}' listening...")
            while True:
                entries = client.xreadgroup(
                    groupname=GROUP_NAME,
                    consumername=consumer_name,
                    streams={STREAM_KEY: ">"},
                    count=10,
                    block=5000,
                )
                if not entries:
                    continue
                for _, messages in entries:
                    for message_id, payload in messages:
                        print(f"Processing {message_id} payload={payload}")
                        time.sleep(0.2)
                        client.xack(STREAM_KEY, GROUP_NAME, message_id)
        except Exception as exc:
            print(f"Consumer error: {exc}. reconnecting in 2s...")
            time.sleep(2)
        finally:
            if client:
                close_client(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redis Streams example")
    parser.add_argument("mode", choices=["producer", "consumer"])
    parser.add_argument("--consumer", default="worker-1")
    parser.add_argument("--order-id", default="order-1001")
    parser.add_argument("--customer-id", default="cust-2002")
    args = parser.parse_args()

    if args.mode == "producer":
        produce(args.order_id, args.customer_id)
    else:
        consume(args.consumer)
