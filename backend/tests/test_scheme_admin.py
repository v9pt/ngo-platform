"""Creating and editing schemes, rule validation, publish guards, hand-written summaries,
call-backs and reports."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

from app.eligibility import rule_problem
from app.seed import SAMPLE_PAID, run_seed
from tests.conftest import TEST_DB_URL, make_config

PASSWORD = "DemoPass#2026"


async def _login(client: AsyncClient, who: str) -> None:
    client.cookies.clear()
    r = await client.post(
        "/v1/auth/login", json={"email": f"{who}@demo.example", "password": PASSWORD}
    )
    assert r.status_code == 200


@pytest.fixture
async def seeded(client: AsyncClient) -> AsyncClient:
    run_seed(TEST_DB_URL, PASSWORD, make_config())
    return client


@pytest.mark.parametrize(
    "rule",
    [
        {"field": "age", "op": "gte", "value": 18},
        {"field": "age", "op": "between", "value": [18, 60]},
        {"field": "pregnant", "op": "eq", "value": True},
        {"field": "marital_status", "op": "eq", "value": "widow"},
        {"field": "district", "op": "in", "value": ["Bhopal"]},
    ],
)
def test_valid_rules_pass(rule: dict[str, Any]) -> None:
    assert rule_problem(rule) is None


@pytest.mark.parametrize(
    "rule",
    [
        {"field": "income", "op": "gte", "value": 1},
        {"field": "age", "op": "between", "value": [60, 18]},
        {"field": "age", "op": "gte", "value": 999},
        {"field": "age", "op": "eq", "value": 18},
        {"field": "pregnant", "op": "eq", "value": "yes"},
        {"field": "marital_status", "op": "eq", "value": "widowed"},
        {"field": "district", "op": "in", "value": []},
    ],
)
def test_broken_rules_are_refused(rule: dict[str, Any]) -> None:
    assert rule_problem(rule) is not None


async def test_new_scheme_starts_as_an_unpublishable_draft(seeded: AsyncClient) -> None:
    await _login(seeded, "editor")
    r = await seeded.post(
        "/v1/admin/schemes", json={"title_en": "New", "title_hi": "नई", "need": "health"}
    )
    assert r.status_code == 201
    code = r.json()["code"]
    assert r.json()["status"] == "draft"
    public = await seeded.get(f"/v1/schemes/{code}")
    assert public.status_code == 404
    blocked = await seeded.post(f"/v1/admin/schemes/{code}/transition", json={"to": "in_review"})
    assert blocked.status_code == 409
    assert "rule" in blocked.json()["detail"]


async def test_a_completed_scheme_can_reach_the_public(seeded: AsyncClient) -> None:
    await _login(seeded, "admin")
    code = (
        await seeded.post(
            "/v1/admin/schemes", json={"title_en": "New", "title_hi": "नई", "need": "health"}
        )
    ).json()["code"]
    patched = await seeded.patch(
        f"/v1/admin/schemes/{code}",
        json={
            "benefit_en": "Rs 100",
            "who_can_apply_en": "Women",
            "source_url": "https://example.org/notice",
            "rules": [{"field": "age", "op": "gte", "value": 18}],
        },
    )
    assert patched.status_code == 200
    for to in ("in_review", "published"):
        r = await seeded.post(f"/v1/admin/schemes/{code}/transition", json={"to": to})
        assert r.status_code == 200
    assert (await seeded.get(f"/v1/schemes/{code}")).status_code == 200
    history = (await seeded.get(f"/v1/admin/schemes/{code}/history")).json()
    assert history[0]["detail"]["to"] == "published"
    assert history[0]["actor_name"] == "Meera Admin"


async def test_a_bad_rule_is_refused_and_nothing_changes(seeded: AsyncClient) -> None:
    await _login(seeded, "editor")
    r = await seeded.patch(
        "/v1/admin/schemes/SCH-090", json={"rules": [{"field": "age", "op": "gte", "value": 500}]}
    )
    assert r.status_code == 422
    detail = (await seeded.get("/v1/admin/schemes/SCH-090")).json()
    assert detail["rules"][0]["field"] == "marital_status"


async def test_donor_cannot_create_a_scheme(seeded: AsyncClient) -> None:
    await _login(seeded, "donor")
    r = await seeded.post(
        "/v1/admin/schemes", json={"title_en": "x", "title_hi": "x", "need": "health"}
    )
    assert r.status_code == 403


async def test_hand_written_summary_works_with_no_model_and_passes_the_same_checks(
    seeded: AsyncClient,
) -> None:
    await _login(seeded, "editor")
    assert (await seeded.post("/v1/admin/schemes/SCH-045/summary-draft")).status_code == 503
    bad = await seeded.post(
        "/v1/admin/schemes/SCH-045/summaries",
        json={"hindi_text": "इस योजना में 18 से 45 वर्ष की महिलाओं को हर महीने ₹9,999 मिलते हैं।"},
    )
    assert bad.json()["source"] == "human"
    assert bad.json()["checks"]["needs_attention"] is True
    refused = await seeded.post(f"/v1/admin/summaries/{bad.json()['id']}/approve")
    assert refused.status_code == 409
    good = await seeded.post(
        "/v1/admin/schemes/SCH-045/summaries",
        json={"hindi_text": "इस योजना में 18 से 45 वर्ष की महिलाओं को हर महीने ₹2,000 मिलते हैं।"},
    )
    assert good.json()["checks"]["needs_attention"] is False
    approved = await seeded.post(f"/v1/admin/summaries/{good.json()['id']}/approve")
    assert approved.status_code == 200
    public = (await seeded.get("/v1/schemes/SCH-045")).json()
    assert "₹2,000" in public["summary_hi"]


async def test_browse_filters_by_need_and_district(seeded: AsyncClient) -> None:
    livelihood = (await seeded.get("/v1/schemes", params={"need": "livelihood"})).json()
    assert {s["need"] for s in livelihood} == {"livelihood"}
    dewas = {
        s["code"] for s in (await seeded.get("/v1/schemes", params={"district": "Dewas"})).json()
    }
    assert "SCH-014" in dewas  # runs everywhere
    assert "SCH-040" not in dewas  # limited to four other districts
    bhopal = {
        s["code"] for s in (await seeded.get("/v1/schemes", params={"district": "Bhopal"})).json()
    }
    assert "SCH-040" in bhopal


async def test_a_district_limit_applies_in_the_check_without_a_district_rule(
    seeded: AsyncClient,
) -> None:
    await _login(seeded, "admin")
    await seeded.post("/v1/admin/schemes/SCH-050/transition", json={"to": "draft"})
    await seeded.patch("/v1/admin/schemes/SCH-050", json={"districts": ["Bhopal"]})
    for to in ("in_review", "published"):
        await seeded.post("/v1/admin/schemes/SCH-050/transition", json={"to": to})
    results = (await seeded.post("/v1/schemes/check", json={"age": 40, "district": "Dewas"})).json()
    camp = next(r for r in results if r["code"] == "SCH-050")
    assert camp["status"] == "excluded"


async def test_callback_needs_consent_and_a_valid_mobile(client: AsyncClient) -> None:
    good = {"phone": "9876543210", "consent": True}
    assert (await client.post("/v1/schemes/callbacks", json=good)).status_code == 201
    no_consent = {"phone": "9876543210", "consent": False}
    assert (await client.post("/v1/schemes/callbacks", json=no_consent)).status_code == 422
    for phone in ("12345", "1234567890", "98765432100", "98765abcde"):
        r = await client.post("/v1/schemes/callbacks", json={"phone": phone, "consent": True})
        assert r.status_code == 422
        assert phone not in r.text


async def test_callback_is_rate_limited(client: AsyncClient) -> None:
    body = {"phone": "9876543210", "consent": True}
    for _ in range(5):
        await client.post("/v1/schemes/callbacks", json=body)
    assert (await client.post("/v1/schemes/callbacks", json=body)).status_code == 429


async def test_only_staff_see_callbacks_and_can_close_them(seeded: AsyncClient) -> None:
    assert (await seeded.get("/v1/admin/callbacks")).status_code == 401
    await _login(seeded, "donor")
    assert (await seeded.get("/v1/admin/callbacks")).status_code == 403
    await _login(seeded, "editor")
    rows = (await seeded.get("/v1/admin/callbacks")).json()
    assert len(rows) == 3
    done = await seeded.post(f"/v1/admin/callbacks/{rows[0]['id']}/done")
    assert done.json()["status"] == "done"


async def test_seed_gives_reports_real_numbers_and_stays_idempotent(seeded: AsyncClient) -> None:
    run_seed(TEST_DB_URL, PASSWORD, make_config())
    await _login(seeded, "admin")
    reports = (await seeded.get("/v1/admin/campaigns")).json()
    livelihood = next(r for r in reports if r["slug"] == "womens-livelihood-fund")
    assert livelihood["paid_count"] == sum(1 for row in SAMPLE_PAID if row[1] == 0)
    assert livelihood["failed_count"] == 1
    assert next(r for r in reports if r["slug"] == "winter-warmth-2026")["paid_count"] == 0


async def test_editor_cannot_see_reports_or_run_monthly_charges(seeded: AsyncClient) -> None:
    await _login(seeded, "editor")
    assert (await seeded.get("/v1/admin/campaigns")).status_code == 403
    assert (await seeded.post("/v1/admin/mandates/run")).status_code == 403


async def test_admin_runs_the_due_monthly_charge_once(seeded: AsyncClient) -> None:
    await _login(seeded, "admin")
    first = await seeded.post("/v1/admin/mandates/run")
    assert first.json() == {"charged": 1, "skipped": 0}
    assert (await seeded.post("/v1/admin/mandates/run")).json() == {"charged": 0, "skipped": 0}
