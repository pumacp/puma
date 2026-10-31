"""Shared pytest fixtures."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Make src/puma importable
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(autouse=True)
def _isolate_run_artifacts(tmp_path, monkeypatch):
    """Keep run artefacts out of the checkout (D51, item a).

    ``puma.orchestrator.runner`` writes every run under the cwd-relative
    ``RESULTS_ROOT`` (``results/<run_id>/``) and opens the inference cache at
    the literal ``data/cache/inferences.db``. Tests that exercise the runner
    therefore littered the working tree. This fixture points ``RESULTS_ROOT``
    at ``tmp_path`` and redirects any *relative* cache path there as well;
    absolute paths (the explicit ``tmp_path / "test.db"`` used by the cache
    tests) are left untouched, so no test changes behaviour.
    """
    from puma.orchestrator import runner as runner_mod
    from puma.runtime import cache as cache_mod

    monkeypatch.setattr(runner_mod, "RESULTS_ROOT", tmp_path / "results")

    original_init = cache_mod.InferenceCache.__init__

    def _init(self, db_path=cache_mod._DEFAULT_PATH):
        path = Path(db_path)
        if not path.is_absolute():
            path = tmp_path / path
        original_init(self, db_path=path)

    monkeypatch.setattr(cache_mod.InferenceCache, "__init__", _init)


@pytest.fixture
def ollama_client_mock():
    """Mock Ollama client for tests that do not require a real Ollama server."""
    mock = MagicMock()
    mock.chat.return_value = {"message": {"content": "Critical"}}
    return mock
