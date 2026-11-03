"""Receipt PDF rendering from the immutable receipt snapshot.

WeasyPrint is CPU-bound and blocking, so it runs in a worker thread behind a small
concurrency cap: a burst of downloads cannot starve the event loop or exhaust memory.
"""

from __future__ import annotations

import asyncio
from html import escape

from app.models import Receipt
from app.security import PanCipher, mask_pan

_RENDER_SLOTS = asyncio.Semaphore(2)

_CSS = """
@page { size: A4; margin: 24mm 20mm; }
body { font-family: sans-serif; color: #111; font-size: 11pt; }
h1 { font-size: 18pt; margin: 0 0 4mm; }
table { border-collapse: collapse; width: 100%; margin-top: 8mm; }
td { padding: 2.5mm 0; border-bottom: 1px solid #ccc; vertical-align: top; }
td:first-child { color: #555; width: 38%; }
.note { margin-top: 10mm; font-size: 9pt; color: #555; }
"""


def format_rupees(paise: int) -> str:
    """Indian digit grouping (12,34,567.50) from integer paise."""
    rupees, rem = divmod(paise, 100)
    digits = str(rupees)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups: list[str] = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join([*groups, tail])
    return f"{digits}.{rem:02d}"


def receipt_html(receipt: Receipt, cipher: PanCipher) -> str:
    trust = receipt.trust_snapshot
    pan = (
        mask_pan(cipher.decrypt(receipt.donor_pan_ciphertext))
        if receipt.donor_pan_ciphertext
        else "Not provided"
    )
    rows = [
        ("Receipt number", receipt.number),
        ("Date", receipt.issued_at.strftime("%d %b %Y")),
        ("Received from", receipt.donor_name),
        ("Donor PAN", pan),
        ("Campaign", receipt.campaign_title),
        ("Amount", f"Rs {format_rupees(receipt.amount_paise)}"),
        ("Trust PAN", str(trust.get("pan", ""))),
        ("80G registration", str(trust.get("reg_80g", ""))),
    ]
    body = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>" for k, v in rows)
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<style>{_CSS}</style></head><body>"
        f"<h1>{escape(str(trust.get('name', '')))}</h1><p>Donation receipt</p>"
        f"<table>{body}</table>"
        "<p class='note'>Sample receipt for a demonstration build. "
        "Trust details are placeholders.</p>"
        "</body></html>"
    )


def _render(html: str) -> bytes:
    from weasyprint import HTML  # type: ignore[import-untyped]  # lazy: needs pango at runtime

    pdf: bytes = HTML(string=html).write_pdf()
    return pdf


async def render_receipt_pdf(receipt: Receipt, cipher: PanCipher) -> bytes:
    html = receipt_html(receipt, cipher)
    async with _RENDER_SLOTS:
        return await asyncio.to_thread(_render, html)
