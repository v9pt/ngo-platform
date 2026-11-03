from datetime import date

from sqlalchemy import text

from app.seed import SCHEMES, current_fy, run_seed
from tests.conftest import TEST_DB_URL


def test_current_fy_rolls_over_in_april() -> None:
    assert current_fy(date(2026, 3, 31)) == "2025-26"
    assert current_fy(date(2026, 4, 1)) == "2026-27"
    assert current_fy(date(2026, 11, 3)) == "2026-27"
    assert current_fy(date(2099, 12, 1)) == "2099-00"


async def test_seed_is_idempotent_and_creates_demo_logins(client, app) -> None:  # type: ignore[no-untyped-def]
    first = run_seed(TEST_DB_URL, "DemoPass#2026")
    second = run_seed(TEST_DB_URL, "DemoPass#2026")
    assert first == second
    assert first["schemes"] == len(SCHEMES)
    login = await client.post(
        "/v1/auth/login", json={"email": "admin@demo.example", "password": "DemoPass#2026"}
    )
    assert login.status_code == 200
    assert login.json()["role"] == "admin"
    async with app.state.engine.connect() as conn:
        counter = (await conn.execute(text("SELECT count(*) FROM receipt_counters"))).scalar_one()
    assert counter == 1


def test_every_seeded_scheme_has_rules_and_a_source() -> None:
    for s in SCHEMES:
        assert s["rules"], s["code"]
        assert s["source_url"].startswith("https://")
