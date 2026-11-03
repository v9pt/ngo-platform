"""Receipt PDF rendering from the immutable receipt snapshot.

WeasyPrint is CPU-bound and blocking, so it runs in a worker thread behind a small
concurrency cap: a burst of downloads cannot starve the event loop or exhaust memory.
"""

from __future__ import annotations

import asyncio
from html import escape
from zoneinfo import ZoneInfo

from app.models import Receipt
from app.security import PanCipher, mask_pan

_RENDER_SLOTS = asyncio.Semaphore(2)
IST = ZoneInfo("Asia/Kolkata")

_CSS = """
@page { size: A4; margin: 20mm; }
body {
  font-family: "Noto Sans Devanagari", "Noto Sans", sans-serif;
  color: #1b1f4b; font-size: 11pt;
}
.band { border-top: 3mm solid #b0155e; padding-top: 5mm; }
h1 { font-size: 18pt; margin: 0; }
.kind { font-size: 13pt; font-weight: 700; margin: 6mm 0 0; }
table { border-collapse: collapse; width: 100%; margin-top: 6mm; }
td { padding: 2.5mm 0; border-bottom: 0.3mm solid #c9c9d6; vertical-align: top; }
td:first-child { color: #55587a; width: 38%; }
.statement { margin-top: 8mm; }
.note { margin-top: 10mm; font-size: 9pt; color: #55587a; }
"""

_ONES = [
    *("Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"),
    *("Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen"),
    *("Seventeen", "Eighteen", "Nineteen"),
]
_TENS = ["", "Ten", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_thousand(n: int) -> list[str]:
    words: list[str] = []
    if n >= 100:
        words += [_ONES[n // 100], "Hundred"]
        n %= 100
    if n >= 20:
        words.append(_TENS[n // 10])
        n %= 10
    if n:
        words.append(_ONES[n])
    return words


def rupees_in_words(paise: int) -> str:
    """Amount in words with Indian grouping, as Indian receipts conventionally show it."""
    rupees, rem = divmod(paise, 100)
    words: list[str] = []
    for size, name in ((10_000_000, "Crore"), (100_000, "Lakh"), (1_000, "Thousand")):
        if rupees >= size:
            words += [*_below_thousand(rupees // size), name]
            rupees %= size
    words += _below_thousand(rupees)
    text = " ".join(words) or "Zero"
    tail = f" and {' '.join(_below_thousand(rem))} Paise" if rem else ""
    return f"Rupees {text}{tail} only"


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
    is_80g = receipt.donor_pan_ciphertext is not None
    rows = [
        ("Receipt number", receipt.number),
        ("Date", receipt.issued_at.astimezone(IST).strftime("%d %b %Y")),
        ("Received from", receipt.donor_name),
        ("Donor PAN", pan),
        ("Campaign", receipt.campaign_title),
        ("Amount", f"Rs {format_rupees(receipt.amount_paise)}"),
        ("Amount in words", rupees_in_words(receipt.amount_paise)),
        ("Trust PAN", str(trust.get("pan", ""))),
        ("80G registration", str(trust.get("reg_80g", ""))),
    ]
    body = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>" for k, v in rows)
    kind, statement = (
        (
            "Donation receipt and section 80G certificate",
            "This donation was received by the trust, which is registered under section 80G of "
            "the Income-tax Act, 1961. No goods or services were given in return.",
        )
        if is_80g
        else (
            "Donation receipt",
            "This is a plain receipt. It is not an 80G certificate because no PAN was on file "
            "when the donation was paid.",
        )
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<style>{_CSS}</style></head><body><div class='band'>"
        f"<h1>{escape(str(trust.get('name', '')))}</h1></div>"
        f"<p class='kind'>{kind}</p>"
        f"<table>{body}</table>"
        f"<p class='statement'>{statement}</p>"
        "<p class='note'>Sample document from a demonstration build. Trust details are "
        "placeholders, and it has no value for tax purposes.</p>"
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
