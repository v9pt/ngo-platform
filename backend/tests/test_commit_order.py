"""A client must never hear "done" before the data is saved.

If the response goes out first, a page that refreshes straight away can read the old row, and a
commit that then fails has already told a donor their payment succeeded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from httpx import ASGITransport, AsyncClient
from sqlalchemy import event

from tests.test_donations_api import DONOR

APP_DIR = Path(__file__).resolve().parent.parent / "app"


async def test_the_transaction_commits_before_the_response_starts(app: Any) -> None:
    order: list[str] = []
    event.listen(app.state.engine.sync_engine, "commit", lambda _: order.append("commit"))

    async def recording_app(scope: Any, receive: Any, send: Any) -> None:
        async def recording_send(message: Any) -> None:
            if message["type"] == "http.response.start":
                order.append("response")
            await send(message)

        await app(scope, receive, recording_send)

    transport = ASGITransport(app=recording_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.post("/v1/auth/register", json=DONOR)).status_code == 201

    assert "commit" in order
    assert order.index("commit") < order.index("response")


def test_no_route_uses_the_session_without_the_commit_first_scope() -> None:
    offenders = [
        str(path.relative_to(APP_DIR))
        for path in APP_DIR.rglob("*.py")
        if path.name != "db.py" and "Depends(get_session" in path.read_text()
    ]
    assert offenders == []
