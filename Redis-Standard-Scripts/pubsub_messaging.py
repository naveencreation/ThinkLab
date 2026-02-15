"""Pub/Sub producer + subscriber example with reconnection loop."""

from __future__ import annotations

import argparse
import time

from redis.exceptions import RedisError

from redis_common import close_client, get_redis_client, validate_non_empty


def run_subscriber(channel: str) -> None:
    channel = validate_non_empty(channel, "channel")

    while True:
        client = None
        pubsub = None
        try:
            client = get_redis_client()
            pubsub = client.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(channel)
            print(f"Subscribed to channel: {channel}")
            for message in pubsub.listen():
                payload = message.get("data")
                if payload is not None:
                    print(f"received: {payload}")
        except RedisError as exc:
            print(f"Subscriber error: {exc}. reconnecting in 2s...")
            time.sleep(2)
        finally:
            if pubsub:
                pubsub.close()
            if client:
                close_client(client)


def run_publisher(channel: str, text: str) -> None:
    channel = validate_non_empty(channel, "channel")
    text = validate_non_empty(text, "text", max_len=2048)

    client = get_redis_client()
    try:
        sent = client.publish(channel, text)
        print(f"Published to {channel}. subscribers_reached={sent}")
    finally:
        close_client(client)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Redis Pub/Sub example")
    parser.add_argument("mode", choices=["subscriber", "publisher"])
    parser.add_argument("--channel", default="events.notifications")
    parser.add_argument("--message", default="hello from publisher")
    args = parser.parse_args()

    if args.mode == "subscriber":
        run_subscriber(args.channel)
    else:
        run_publisher(args.channel, args.message)
