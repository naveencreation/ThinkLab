"""Leaderboard example using sorted sets with pagination."""

from __future__ import annotations

from redis_common import close_client, get_redis_client


LEADERBOARD_KEY = "leaderboard:season-1"


def add_score(client, player_id: str, delta: float) -> float:
    return float(client.zincrby(LEADERBOARD_KEY, delta, player_id))


def top_players(client, limit: int = 10):
    return client.zrevrange(LEADERBOARD_KEY, 0, limit - 1, withscores=True)


def player_rank(client, player_id: str):
    rank = client.zrevrank(LEADERBOARD_KEY, player_id)
    score = client.zscore(LEADERBOARD_KEY, player_id)
    return rank, score


def main() -> None:
    client = get_redis_client()
    try:
        add_score(client, "player-a", 150)
        add_score(client, "player-b", 230)
        add_score(client, "player-c", 120)

        print("Top players:", top_players(client, 3))
        print("player-a rank/score:", player_rank(client, "player-a"))
    finally:
        close_client(client)


if __name__ == "__main__":
    main()
