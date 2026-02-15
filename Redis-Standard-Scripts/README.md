# Redis Standard Scripts (Production-Oriented Examples)

This folder includes practical Redis implementations for common backend patterns:

- Caching patterns (basic key-value, TTL, cache-aside, write-through)
- Pub/Sub messaging
- Streams with consumer groups
- Distributed locking
- Rate limiting
- Background job queues
- Transactions and pipelines
- Lua scripting
- Session storage
- Leaderboards with sorted sets

## 1) Prerequisites

- Python 3.10+
- Docker + Docker Compose

## 2) Setup

```bash
cd Redis-Standard-Scripts
cp .env.example .env
# Edit .env and set a strong REDIS_PASSWORD
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3) Run Redis via Docker

```bash
docker compose up -d
docker compose ps
```

Check health:

```bash
docker compose logs redis --tail=50
```

## 4) Run Examples

```bash
python caching_patterns.py
python pubsub_messaging.py subscriber --channel events.notifications
python pubsub_messaging.py publisher --channel events.notifications --message "hello"
python streams_consumer_groups.py consumer --consumer worker-1
python streams_consumer_groups.py producer --order-id order-123 --customer-id cust-1
python distributed_locking.py --lock locks.inventory-update --worker worker-1
python rate_limiting.py
python background_job_queue.py worker
python background_job_queue.py enqueue --type send_email --payload '{"to":"user@example.com"}'
python transactions_and_pipelines.py
python lua_scripting.py
python session_storage.py
python leaderboard_sorted_sets.py
```

## 5) Security Best Practices Implemented

- `AUTH` enforced in code (`REDIS_PASSWORD` required).
- Optional TLS support (`REDIS_USE_TLS=true` and cert paths in `.env`).
- Input validation helpers for user-supplied fields.
- Timeouts enabled for connect/socket operations.
- Defensive retries on transient connection/time-out failures.
- Docker config includes `--protected-mode yes` and persistence (`AOF`).

## 6) Scalability Considerations

- Use separate Redis instances/logical DBs per workload class (cache, queue, sessions) to reduce noisy-neighbor impact.
- For high write volumes, shard keys with consistent hashing (e.g., `session:{tenant}:{user}`).
- Move to Redis Sentinel/Cluster for HA and horizontal scale.
- For queues/streams, run multiple workers with distinct consumer names.
- Apply backpressure in workers (batch size and sleep tuning).

## 7) Performance Optimizations

- Use pipelines for bulk writes/reads (`transactions_and_pipelines.py`).
- Bound memory growth with TTLs/max lengths (`setex`, `XADD ... MAXLEN`).
- Use sorted sets and stream groups for O(log N) access/update patterns.
- Enable `hiredis` parser (included via `redis[hiredis]`).
- Keep payloads compact; prefer IDs over large blobs.

## 8) Notes for Production

- Rotate passwords and manage secrets using a vault (not plaintext files).
- Enable mTLS in production if required by policy.
- Add metrics/observability (latency, hit ratio, queue depth, pending stream entries).
- Add dead-letter handling and retry caps for job workers.
