"""Public schemes endpoints: only published schemes, eligibility check shows its reasoning."""

from httpx import AsyncClient

from app.seed import SCHEMES, run_seed
from tests.conftest import TEST_DB_URL

PUBLISHED = [s["code"] for s in SCHEMES if s["status"] == "published"]


async def _seeded(client: AsyncClient) -> None:
    run_seed(TEST_DB_URL, "DemoPass#2026")


async def test_list_returns_only_published_schemes(client: AsyncClient) -> None:
    await _seeded(client)
    rows = (await client.get("/v1/schemes")).json()
    assert sorted(r["code"] for r in rows) == sorted(PUBLISHED)
    assert "notice_text" not in rows[0] and "rules" not in rows[0]


async def test_list_filters_by_need(client: AsyncClient) -> None:
    await _seeded(client)
    all_rows = (await client.get("/v1/schemes")).json()
    need = all_rows[0]["need"]
    rows = (await client.get("/v1/schemes", params={"need": need})).json()
    assert rows and all(r["need"] == need for r in rows)


async def test_detail_of_published_scheme_and_404_for_unpublished(client: AsyncClient) -> None:
    await _seeded(client)
    ok = await client.get(f"/v1/schemes/{PUBLISHED[0]}")
    assert ok.status_code == 200 and ok.json()["source_url"]
    hidden = next(s["code"] for s in SCHEMES if s["status"] != "published")
    assert (await client.get(f"/v1/schemes/{hidden}")).status_code == 404


async def test_check_returns_status_and_rules_for_every_published_scheme(
    client: AsyncClient,
) -> None:
    await _seeded(client)
    r = await client.post(
        "/v1/schemes/check",
        json={"age": 35, "marital_status": "widow", "has_bpl_card": True},
    )
    assert r.status_code == 200
    results = r.json()
    assert sorted(x["code"] for x in results) == sorted(PUBLISHED)
    assert {x["status"] for x in results} <= {"match", "possible", "excluded"}
    assert all(isinstance(x["rules"], list) for x in results)
    # Best matches first.
    order = {"match": 0, "possible": 1, "excluded": 2}
    ranks = [order[x["status"]] for x in results]
    assert ranks == sorted(ranks)


async def test_check_rejects_unknown_fields_and_absurd_ages(client: AsyncClient) -> None:
    assert (await client.post("/v1/schemes/check", json={"income": 5})).status_code == 422
    assert (await client.post("/v1/schemes/check", json={"age": 400})).status_code == 422
