"""Tests for Operations Dashboard imports and initialization safety."""

import importlib.util
import sys
from pathlib import Path


def test_operations_dashboard_imports() -> None:
    """Verify that the Operations Dashboard can be imported without ImportError."""
    project_root = Path(__file__).resolve().parent.parent
    pages_dir = project_root / "src" / "content_creation" / "ui" / "pages"
    dashboard_path = pages_dir / "6_operations_dashboard.py"

    assert dashboard_path.exists(), f"Dashboard file not found at {dashboard_path}"

    # Load module dynamically because file name starts with a digit
    spec = importlib.util.spec_from_file_location("operations_dashboard", str(dashboard_path))
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules["operations_dashboard"] = module

    # Executing the module will trigger the imports inside the module
    # We want to ensure no ImportError is raised during this execution.
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # If streamlit isn't fully initialized, some streamlit calls might fail,
        # but the imports themselves must not fail with ImportError for job schema.
        if isinstance(e, ImportError):
            raise e

    assert hasattr(module, "_build_snapshot")
    assert hasattr(module, "main")
