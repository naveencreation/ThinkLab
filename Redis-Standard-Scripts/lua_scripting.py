"""Lua scripting for atomic multi-key stock reservation."""

from __future__ import annotations

from redis_common import close_client, get_redis_client


RESERVE_STOCK_SCRIPT = """
local stock_key = KEYS[1]
local reserved_key = KEYS[2]
local qty = tonumber(ARGV[1])

local current = tonumber(redis.call('GET', stock_key) or '0')
if current < qty then
  return {0, current}
end

redis.call('DECRBY', stock_key, qty)
redis.call('INCRBY', reserved_key, qty)
return {1, current - qty}
"""


def main() -> None:
    client = get_redis_client()
    try:
        client.set("stock:item-101", 10)
        client.set("reserved:item-101", 0)

        result = client.eval(RESERVE_STOCK_SCRIPT, 2, "stock:item-101", "reserved:item-101", 3)
        success, remaining = int(result[0]), int(result[1])
        print(f"reserve success={bool(success)} remaining_stock={remaining}")
    finally:
        close_client(client)


if __name__ == "__main__":
    main()
