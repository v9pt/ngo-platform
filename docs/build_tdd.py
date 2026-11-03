"""Builds docs/TDD.pdf from docs/TDD.html. Run with the backend venv, which has WeasyPrint."""

from pathlib import Path

from weasyprint import HTML

here = Path(__file__).resolve().parent
HTML(filename=str(here / "TDD.html"), base_url=str(here)).write_pdf(here / "TDD.pdf")
print(here / "TDD.pdf")
