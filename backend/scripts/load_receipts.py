"""Measures receipt issuing through the running API, then checks the numbers have no gaps.

Run against a throwaway database, never a real one: it creates donations and immutable receipts.

    API=http://localhost:8001 DATABASE_URL=postgresql+psycopg://... \
        python scripts/load_receipts.py --payments 1000 --concurrency 50
"""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time
import uuid

import httpx
from sqlalchemy import create_engine, text

GOOD_CARD = {"card_number": "4242424242424242", "issuing_country": "IN"}


async def pay(client: httpx.AsyncClient, slug: str, gate: asyncio.Semaphore) -> float:
    async with gate:
        created = await client.post(
            "/v1/donations",
            json={"campaign_slug": slug, "amount_paise": 50_000},
            headers={"Idempotency-Key": uuid.uuid4().hex},
        )
        created.raise_for_status()
        started = time.perf_counter()
        paid = await client.post(
            f"/v1/donations/{created.json()['id']}/test-charge", json=GOOD_CARD
        )
        paid.raise_for_status()
        assert paid.json()["receipt_number"]  # noqa: S101
        return time.perf_counter() - started


async def run(base: str, payments: int, concurrency: int) -> None:
    limits = httpx.Limits(max_connections=concurrency)
    async with httpx.AsyncClient(base_url=base, timeout=60, limits=limits) as client:
        account = {
            "email": f"load-{uuid.uuid4().hex[:8]}@demo.example",
            "password": "a-long-password-1",
            "full_name": "Load Test",
        }
        (await client.post("/v1/auth/register", json=account)).raise_for_status()
        slug = (await client.get("/v1/campaigns")).json()[0]["slug"]
        gate = asyncio.Semaphore(concurrency)
        started = time.perf_counter()
        times = await asyncio.gather(*(pay(client, slug, gate) for _ in range(payments)))
        elapsed = time.perf_counter() - started
    times.sort()
    print(f"payments={payments} concurrency={concurrency} elapsed={elapsed:.1f}s")  # noqa: T201
    print(f"throughput={payments / elapsed:.1f}/s")  # noqa: T201
    print(  # noqa: T201
        f"charge latency median={statistics.median(times) * 1000:.0f}ms "
        f"p95={times[int(len(times) * 0.95)] * 1000:.0f}ms max={times[-1] * 1000:.0f}ms"
    )


def check_gapless(url: str) -> None:
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT fy, count(*), min(seq), max(seq), count(DISTINCT seq) "
                "FROM receipts GROUP BY fy"
            )
        ).all()
    engine.dispose()
    for fy, count, low, high, distinct in rows:
        ok = low == 1 and high == count and distinct == count
        print(f"fy={fy} receipts={count} max_seq={high} gapless_and_unique={ok}")  # noqa: T201


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--payments", type=int, default=1000)
    parser.add_argument("--concurrency", type=int, default=50)
    args = parser.parse_args()
    asyncio.run(
        run(os.environ.get("API", "http://localhost:8001"), args.payments, args.concurrency)
    )
    check_gapless(os.environ["DATABASE_URL"])
