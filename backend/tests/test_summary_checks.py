"""Deterministic checks run on AI-drafted Hindi summaries before an editor sees them."""

from app.summary_checks import run_checks

SOURCE = (
    "Eligible widows aged 18 to 79 with a BPL card receive Rs 600 a month. Loan up to Rs 3,00,000."
)
GOOD = "यह योजना 18 से 79 वर्ष की विधवा महिलाओं के लिए है। उन्हें हर महीने ₹600 मिलते हैं। ऋण ₹3 लाख तक।"


def test_good_hindi_summary_passes_everything() -> None:
    c = run_checks(GOOD, SOURCE)
    assert c["numbers_match_source"] and c["length_ok"] and c["devanagari_ok"]
    assert c["needs_attention"] is False


def test_number_not_in_source_is_flagged_and_named() -> None:
    c = run_checks(GOOD.replace("₹600", "₹900"), SOURCE)
    assert c["numbers_match_source"] is False
    assert c["unmatched_numbers"] == [900]
    assert c["needs_attention"] is True


def test_devanagari_digits_and_commas_are_normalised() -> None:
    assert run_checks("हर महीने ₹६०० मिलते हैं, यह योजना महिलाओं के लिए है।" * 1, SOURCE)[
        "numbers_match_source"
    ]


def test_english_text_fails_the_script_check() -> None:
    c = run_checks(
        "This scheme pays Rs 600 a month to eligible widows aged 18 to 79 years.", SOURCE
    )
    assert c["devanagari_ok"] is False and c["needs_attention"] is True


def test_too_short_or_too_long_fails_length() -> None:
    assert run_checks("पेंशन ₹600", SOURCE)["length_ok"] is False
    assert run_checks("पेंशन योजना " * 200, SOURCE)["length_ok"] is False


def test_empty_summary_does_not_crash() -> None:
    assert run_checks("", SOURCE)["needs_attention"] is True
