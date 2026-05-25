"""Smoke tests for the PUMA Streamlit dashboard.

These tests cover three layers:
- module imports for the helpers that have no top-level streamlit dependency,
- data loaders return empty (not crash) when the DB is absent,
- full AppTest render of `app.py` against the live DB if one is present.

`app.py` executes top-level streamlit calls (st.set_page_config, st.sidebar.*),
so it cannot be imported directly outside a Streamlit runtime. Use AppTest
for end-to-end rendering instead.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
APP_PATH = REPO_ROOT / "src" / "puma" / "dashboard" / "app.py"


@pytest.mark.unit
def test_app_module_parses() -> None:
    """app.py must be syntactically valid Python."""
    ast.parse(APP_PATH.read_text(encoding="utf-8"))


@pytest.mark.unit
def test_components_importable() -> None:
    from puma.dashboard import components

    assert callable(components.metric_card)
    assert callable(components.comparison_table)
    assert callable(components.reliability_plot)
    assert callable(components.pareto_scatter)
    assert callable(components.fig_to_bytes)


@pytest.mark.unit
def test_data_loaders_exposed() -> None:
    from puma.dashboard import data

    for name in (
        "load_runs",
        "load_metrics",
        "load_predictions",
        "load_predictions_with_gold",
        "load_emissions",
        "load_sustainability",
        "load_profile_snapshots",
        "metrics_pivot",
        "run_summary",
    ):
        assert callable(getattr(data, name)), f"data.{name} missing or not callable"


@pytest.mark.unit
def test_loaders_handle_missing_db(tmp_path: Path) -> None:
    """All loaders return empty DataFrame (no crash) when the DB doesn't exist."""
    from puma.dashboard.data import (
        load_emissions,
        load_metrics,
        load_predictions,
        load_predictions_with_gold,
        load_runs,
        load_sustainability,
        metrics_pivot,
        run_summary,
    )

    missing = tmp_path / "does_not_exist.db"
    assert load_runs(missing).empty
    assert load_metrics(missing).empty
    assert load_predictions(missing).empty
    assert load_predictions_with_gold(missing).empty
    assert load_emissions(missing).empty
    assert load_sustainability(missing).empty
    assert metrics_pivot(missing).empty
    assert run_summary(missing) == []


@pytest.mark.unit
def test_load_predictions_with_gold_exposes_gold_column(tmp_path: Path) -> None:
    """When the DB has predictions + instances, the loader must surface gold_label."""
    import sqlite3

    db = tmp_path / "tiny.db"
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE predictions (run_id TEXT, instance_id TEXT, model TEXT, "
        "strategy TEXT, parsed_label TEXT, confidence REAL, logprobs_json TEXT, "
        "latency_ms REAL, tokens_in INT, tokens_out INT, perturbation TEXT, "
        "seed INT, prompt_hash TEXT, raw_response TEXT)"
    )
    con.execute(
        "CREATE TABLE instances (instance_id TEXT, dataset TEXT, source_id TEXT, "
        "input_text TEXT, gold_label TEXT)"
    )
    con.execute(
        "INSERT INTO predictions VALUES "
        "('r1', 'i1', 'm1', 'zero-shot', 'Critical', 0.9, NULL, 1.0, 1, 1, NULL, 42, 'h', 'Critical')"
    )
    con.execute(
        "INSERT INTO instances VALUES ('i1', 'triage_jira', 'i1', 'sample text', 'Critical')"
    )
    con.commit()
    con.close()

    from puma.dashboard.data import load_predictions_with_gold

    df = load_predictions_with_gold(db_path=db)
    assert "gold_label" in df.columns
    assert "input_text" in df.columns
    assert len(df) == 1
    assert df.iloc[0]["gold_label"] == "Critical"
    assert df.iloc[0]["input_text"] == "sample text"


@pytest.mark.unit
@pytest.mark.skipif(
    importlib.util.find_spec("streamlit.testing.v1") is None,
    reason="streamlit.testing.v1 not available",
)
def test_app_renders_without_exception() -> None:
    """End-to-end: streamlit AppTest must execute app.py top-to-bottom."""
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception, f"Dashboard raised: {at.exception}"


# ── Sprint 6 additions: refactor, polish, and tour ────────────────────────────


@pytest.mark.unit
def test_each_view_module_exposes_render() -> None:
    """Each of the 7 view modules must define a callable ``render()``."""
    from puma.dashboard.views import (
        fairness,
        instance_drilldown,
        model_comparison,
        overview,
        reliability,
        robustness,
        sustainability,
    )

    for module in (
        overview,
        model_comparison,
        reliability,
        robustness,
        fairness,
        sustainability,
        instance_drilldown,
    ):
        assert callable(getattr(module, "render", None)), f"{module.__name__} missing render()"


@pytest.mark.unit
def test_app_router_exposes_views_dict() -> None:
    """The router registers exactly 8 views, one per module."""
    src = APP_PATH.read_text(encoding="utf-8")
    # Quick textual check: 8 emoji-prefixed view labels
    expected = [
        "📊 Overview",
        "🆚 Model Comparison",
        "🎯 Reliability",
        "🛡️ Robustness",
        "⚖️ Fairness",
        "🌱 Sustainability Frontier",
        "🔍 Instance Drill-down",
        "🤝 Community",
    ]
    for label in expected:
        assert label in src, f"View label {label!r} not registered in router"


@pytest.mark.unit
def test_components_metric_card_accepts_help_kwarg() -> None:
    """``metric_card`` must expose ``help=`` (Sprint 6 mejora #4)."""
    import inspect

    from puma.dashboard.components import metric_card

    sig = inspect.signature(metric_card)
    assert "help" in sig.parameters


@pytest.mark.unit
def test_components_expose_polish_helpers() -> None:
    """The polish helpers added in Sprint 6 must be importable."""
    from puma.dashboard.components import download_csv_button, empty_filtered_state

    assert callable(empty_filtered_state)
    assert callable(download_csv_button)


@pytest.mark.unit
def test_data_loaders_have_cache_decorator() -> None:
    """Loaders must be wrapped by ``st.cache_data`` (Sprint 6 mejora #1).

    Streamlit's cache decorator attaches a ``clear`` method to the wrapped
    function; absence of that attribute means the loader was not cached.
    """
    from puma.dashboard import data

    for name in (
        "load_runs",
        "load_metrics",
        "load_predictions",
        "load_predictions_with_gold",
        "load_emissions",
        "load_sustainability",
        "load_profile_snapshots",
        "metrics_pivot",
    ):
        fn = getattr(data, name)
        assert hasattr(fn, "clear"), f"data.{name} is not decorated with @st.cache_data"
