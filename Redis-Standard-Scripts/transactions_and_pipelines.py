"""Redis transactions and pipeline batching examples."""

from __future__ import annotations

from redis.exceptions import WatchError

from redis_common import close_client, get_redis_client


def pipeline_batch_example(client) -> None:
    pipe = client.pipeline(transaction=False)
    for i in range(1, 6):
        pipe.set(f"batch:key:{i}", i)
    results = pipe.execute()
    print(f"Pipeline wrote {len(results)} keys")


def atomic_increment_transaction(client, key: str) -> int:
    with client.pipeline() as pipe:
        while True:
            try:
                pipe.watch(key)
                current = pipe.get(key)
                value = int(current or 0)
                pipe.multi()
                pipe.set(key, value + 1)
                pipe.execute()
                return value + 1
            except WatchError:
                continue
            finally:
                pipe.reset()


def main() -> None:
    client = get_redis_client()
    try:
        pipeline_batch_example(client)
        updated = atomic_increment_transaction(client, "counter:orders")
        print(f"Transactional increment -> {updated}")
    finally:
        close_client(client)


if __name__ == "__main__":
    main()
