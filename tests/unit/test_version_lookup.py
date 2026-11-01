"""The installed-version lookups must query the ``puma-cp`` distribution (D50).

The PyPI distribution has been named ``puma-cp`` since the S12.15 hardening while
the import package stays ``puma``; querying ``version("puma")`` raised
``PackageNotFoundError`` everywhere and every surface showed ``0.0.0-unknown``.
"""

from __future__ import annotations

import importlib
from importlib.metadata import PackageNotFoundError

import pytest

import puma
from puma.diagnostics import env as env_mod
from puma.orchestrator import runner as runner_mod
from puma.ui import banner as banner_mod

_FALLBACK = "0.0.0-unknown"


def _recording_version(result: str):
    seen: list[str] = []

    def fake(name: str) -> str:
        seen.append(name)
        return result

    return fake, seen


def _raising_version(name: str) -> str:
    raise PackageNotFoundError(name)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("target", "resolve"),
    [
        ("puma.ui.banner.version", banner_mod._resolve_puma_version),
        ("puma.diagnostics.env.version", env_mod._resolve_puma_version),
        # runner.py imports ``version`` inside the function, so patch the source.
        ("importlib.metadata.version", runner_mod._resolve_runner_puma_version),
    ],
    ids=["banner", "env", "runner"],
)
def test_resolvers_query_the_puma_cp_distribution(monkeypatch, target, resolve):
    fake, seen = _recording_version("9.9.9")
    monkeypatch.setattr(target, fake)
    assert resolve() == "9.9.9"
    assert seen == ["puma-cp"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("target", "resolve"),
    [
        ("puma.ui.banner.version", banner_mod._resolve_puma_version),
        ("puma.diagnostics.env.version", env_mod._resolve_puma_version),
        ("importlib.metadata.version", runner_mod._resolve_runner_puma_version),
    ],
    ids=["banner", "env", "runner"],
)
def test_resolvers_fall_back_when_distribution_is_missing(monkeypatch, target, resolve):
    monkeypatch.setattr(target, _raising_version)
    assert resolve() == _FALLBACK


@pytest.mark.unit
def test_package_version_queries_puma_cp_and_falls_back(monkeypatch):
    fake, seen = _recording_version("9.9.9")
    monkeypatch.setattr("importlib.metadata.version", fake)
    importlib.reload(puma)
    assert puma.__version__ == "9.9.9"
    assert seen == ["puma-cp"]

    monkeypatch.setattr("importlib.metadata.version", _raising_version)
    importlib.reload(puma)
    assert puma.__version__ == _FALLBACK

    monkeypatch.undo()
    importlib.reload(puma)  # restore the real value for later tests
    assert puma.__version__ != "2.0.0-dev"
