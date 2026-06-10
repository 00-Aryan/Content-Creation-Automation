"""
CI guard: verify all Streamlit page files parse without syntax errors.

Runs ast.parse() on every .py file in the UI pages directory.
If any file has a SyntaxError or IndentationError, the test fails
with the exact file name, line number, and error message — so it
is caught by CI before reaching the Render deployment.
"""
import ast
import pathlib

import pytest

UI_PAGES_DIR = pathlib.Path("src/content_creation/ui/pages")


def _get_page_files():
    if not UI_PAGES_DIR.exists():
        return []
    return sorted(UI_PAGES_DIR.glob("*.py"))


@pytest.mark.parametrize("page_file", _get_page_files(), ids=lambda p: p.name)
def test_page_parses_without_syntax_error(page_file: pathlib.Path) -> None:
    """Each UI page must be parseable by Python's AST.

    A SyntaxError here means the page would crash on load in Render.
    """
    source = page_file.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(page_file))
    except SyntaxError as exc:
        pytest.fail(
            f"\n\nSyntax error in {page_file.name}"
            f"\n  Line {exc.lineno}: {exc.msg}"
            f"\n  Text: {exc.text!r}"
            f"\n\nThis would crash the page on Render. Fix the indentation or syntax error."
        )
