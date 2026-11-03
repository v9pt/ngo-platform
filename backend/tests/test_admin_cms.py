"""Admin CMS: role-gated workflow draft -> in_review -> published, and AI summary drafts."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient

from app.seed import run_seed
from tests.conftest import TEST_DB_URL

PW = "DemoPass#2026"
GOOD_HI = "यह योजना 18 से 79 वर्ष की विधवा महिलाओं के लिए है। उन्हें हर महीने ₹600 मिलते हैं।"
BAD_HI = "यह योजना 18 से 79 वर्ष की विधवा महिलाओं के लिए है। उन्हें हर महीने ₹900 मिलते हैं।"


class StubGenerator:
    def __init__(self, text: str = GOOD_HI) -> None:
        self.text = text
        self.seen_notice: str | None = None

    async def generate(self, notice: str) -> str:
        self.seen_notice = notice
        return self.text


async def _login(client: AsyncClient, who: str) -> None:
    run_seed(TEST_DB_URL, PW)
    client.cookies.clear()
    r = await client.post("/v1/auth/login", json={"email": f"{who}@demo.example", "password": PW})
    assert r.status_code == 200


async def _set_notice(client: AsyncClient, code: str, notice: str) -> None:
    r = await client.patch(f"/v1/admin/schemes/{code}", json={"notice_text": notice})
    assert r.status_code == 200, r.text


# --- access control ---------------------------------------------------------------------


async def test_anonymous_and_donor_cannot_use_admin_api(client: AsyncClient) -> None:
    assert (await client.get("/v1/admin/schemes")).status_code == 401
    await _login(client, "donor")
    assert (await client.get("/v1/admin/schemes")).status_code == 403


async def test_editor_lists_all_schemes_including_unpublished(client: AsyncClient) -> None:
    await _login(client, "editor")
    rows = (await client.get("/v1/admin/schemes")).json()
    assert {r["status"] for r in rows} >= {"published", "in_review"}


# --- workflow ---------------------------------------------------------------------------


async def test_editor_submits_for_review_but_only_admin_publishes(client: AsyncClient) -> None:
    await _login(client, "editor")
    codes = {r["status"]: r["code"] for r in (await client.get("/v1/admin/schemes")).json()}
    in_review = codes["in_review"]
    assert (
        await client.post(f"/v1/admin/schemes/{in_review}/transition", json={"to": "published"})
    ).status_code == 403
    await _login(client, "admin")
    ok = await client.post(f"/v1/admin/schemes/{in_review}/transition", json={"to": "published"})
    assert ok.status_code == 200 and ok.json()["status"] == "published"
    public = await client.get(f"/v1/schemes/{in_review}")
    assert public.status_code == 200


async def test_illegal_transition_is_409_and_nothing_changes(client: AsyncClient) -> None:
    await _login(client, "admin")
    rows = (await client.get("/v1/admin/schemes")).json()
    published = next(r["code"] for r in rows if r["status"] == "published")
    r = await client.post(f"/v1/admin/schemes/{published}/transition", json={"to": "in_review"})
    assert r.status_code == 409


async def test_published_scheme_cannot_be_edited_in_place(client: AsyncClient) -> None:
    await _login(client, "editor")
    rows = (await client.get("/v1/admin/schemes")).json()
    published = next(r["code"] for r in rows if r["status"] == "published")
    r = await client.patch(f"/v1/admin/schemes/{published}", json={"benefit_hi": "x"})
    assert r.status_code == 409


async def test_edit_rejects_fields_that_are_not_editable(client: AsyncClient) -> None:
    await _login(client, "editor")
    rows = (await client.get("/v1/admin/schemes")).json()
    draft = next(r["code"] for r in rows if r["status"] == "in_review")
    r = await client.patch(f"/v1/admin/schemes/{draft}", json={"status": "published"})
    assert r.status_code == 422


async def test_transitions_are_written_to_the_audit_log(client: AsyncClient, app: Any) -> None:
    await _login(client, "admin")
    rows = (await client.get("/v1/admin/schemes")).json()
    code = next(r["code"] for r in rows if r["status"] == "in_review")
    await client.post(f"/v1/admin/schemes/{code}/transition", json={"to": "published"})
    from sqlalchemy import text

    async with app.state.engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT action, detail FROM audit_log WHERE entity='scheme' ORDER BY id DESC")
            )
        ).first()
    assert row is not None and row.action == "scheme.transition"
    assert row.detail["from"] == "in_review" and row.detail["to"] == "published"


# --- AI summaries -----------------------------------------------------------------------

NOTICE = "Eligible widows aged 18 to 79 with a BPL card receive Rs 600 a month."


async def _draft_scheme(client: AsyncClient, app: Any) -> str:
    rows = (await client.get("/v1/admin/schemes")).json()
    code = next(r["code"] for r in rows if r["status"] == "in_review")
    await _set_notice(client, code, NOTICE)
    return str(code)


async def test_ai_draft_is_saved_as_draft_with_checks_and_notice_is_passed_as_data(
    client: AsyncClient, app: Any
) -> None:
    await _login(client, "editor")
    gen = StubGenerator()
    app.state.summary_generator = gen
    code = await _draft_scheme(client, app)
    r = await client.post(f"/v1/admin/schemes/{code}/summary-draft")
    assert r.status_code == 201
    body = r.json()
    assert body["source"] == "ai" and body["status"] == "draft"
    assert body["checks"]["needs_attention"] is False
    assert gen.seen_notice == NOTICE


async def test_ai_draft_with_a_number_not_in_the_notice_cannot_be_approved(
    client: AsyncClient, app: Any
) -> None:
    await _login(client, "editor")
    app.state.summary_generator = StubGenerator(BAD_HI)
    code = await _draft_scheme(client, app)
    draft = (await client.post(f"/v1/admin/schemes/{code}/summary-draft")).json()
    assert draft["checks"]["unmatched_numbers"] == [900]
    r = await client.post(f"/v1/admin/summaries/{draft['id']}/approve")
    assert r.status_code == 409


async def test_editor_fixes_text_checks_rerun_then_approval_is_recorded(
    client: AsyncClient, app: Any
) -> None:
    await _login(client, "editor")
    app.state.summary_generator = StubGenerator(BAD_HI)
    code = await _draft_scheme(client, app)
    draft = (await client.post(f"/v1/admin/schemes/{code}/summary-draft")).json()
    fixed = await client.patch(f"/v1/admin/summaries/{draft['id']}", json={"hindi_text": GOOD_HI})
    assert fixed.json()["checks"]["needs_attention"] is False
    ok = await client.post(f"/v1/admin/summaries/{draft['id']}/approve")
    assert ok.status_code == 200
    assert ok.json()["status"] == "approved" and ok.json()["approved_by"] is not None


async def test_only_approved_summary_appears_on_the_public_scheme_page(
    client: AsyncClient,
) -> None:
    run_seed(TEST_DB_URL, PW)
    public = (await client.get("/v1/schemes/SCH-014")).json()  # seeded approved human summary
    assert "₹600" in public["summary_hi"]
    shg = (await client.get("/v1/schemes/SCH-022")).json()  # only has an AI draft
    assert shg["summary_hi"] is None


async def test_drafting_without_a_configured_generator_is_503(
    client: AsyncClient, app: Any
) -> None:
    await _login(client, "editor")
    app.state.summary_generator = None
    rows = (await client.get("/v1/admin/schemes")).json()
    code = next(r["code"] for r in rows if r["status"] == "in_review")
    await _set_notice(client, code, NOTICE)
    assert (await client.post(f"/v1/admin/schemes/{code}/summary-draft")).status_code == 503


async def test_drafting_needs_a_notice_text(client: AsyncClient, app: Any) -> None:
    await _login(client, "editor")
    app.state.summary_generator = StubGenerator()
    rows = (await client.get("/v1/admin/schemes")).json()
    code = next(r["code"] for r in rows if r["status"] == "in_review")
    await _set_notice(client, code, "")
    assert (await client.post(f"/v1/admin/schemes/{code}/summary-draft")).status_code == 409


async def test_editor_lists_summaries_of_a_scheme_newest_first(client: AsyncClient) -> None:
    await _login(client, "editor")
    rows = (await client.get("/v1/admin/schemes/SCH-022/summaries")).json()
    assert [r["source"] for r in rows] == ["ai"] and rows[0]["status"] == "draft"
    assert (await client.get("/v1/admin/schemes/NOPE/summaries")).status_code == 404
