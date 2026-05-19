"""Secure credential storage for PUMA Community.

Tokens are persisted to a TOML file in the per-user config directory with mode
0600 (POSIX) — only the owning user can read or write it. The store NEVER logs
or echoes raw token values; the only diagnostic representation is the masked
form produced by :func:`mask_token`.

Cross-platform paths:
    * Linux / macOS: ``~/.config/puma/credentials.toml``
    * Windows: ``%APPDATA%/puma/credentials.toml``
    * Override either via the ``PUMA_CONFIG_DIR`` environment variable.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Final

import tomli_w

log = logging.getLogger("puma.community.credentials")

_FILE_NAME: Final[str] = "credentials.toml"
_DIR_MODE: Final[int] = 0o700
_FILE_MODE: Final[int] = 0o600
_TABLE_NAME: Final[str] = "tokens"

# Compiled regex per service. Token shape is validated locally before any
# remote call so a typo never lands as an "invalid token" error from a
# third-party API later in the flow.
SERVICE_TOKEN_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "github": re.compile(r"^(ghp_|github_pat_)[A-Za-z0-9_]{30,}$"),
    "huggingface": re.compile(r"^hf_[A-Za-z0-9]{30,}$"),
    "zenodo": re.compile(r"^[A-Za-z0-9]{60}$"),
    "discord_webhook": re.compile(r"^https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_\-]+$"),
    "telegram_bot": re.compile(r"^\d+:[A-Za-z0-9_\-]{35,}$"),
    "telegram_chat_id": re.compile(r"^-?\d+$"),
}

SUPPORTED_SERVICES: Final[tuple[str, ...]] = tuple(SERVICE_TOKEN_PATTERNS.keys())


class CredentialError(Exception):
    """Base class for credential-storage failures."""


class InsecurePermissionsError(CredentialError):
    """File mode on the credential file is more permissive than 0600."""


class InvalidTokenFormatError(CredentialError):
    """The supplied token does not match the expected pattern for the service."""


def _default_config_dir() -> Path:
    """Return the canonical per-user config directory for PUMA.

    Honors ``PUMA_CONFIG_DIR`` for tests. Otherwise:
        * Windows: ``%APPDATA%/puma``
        * POSIX:   ``~/.config/puma``
    """
    override = os.environ.get("PUMA_CONFIG_DIR")
    if override:
        return Path(override)
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "puma"
        return Path.home() / "AppData" / "Roaming" / "puma"
    return Path.home() / ".config" / "puma"


def mask_token(token: str) -> str:
    """Return a non-secret representation of ``token``.

    The result preserves only enough surface to identify which token is in use
    (an optional prefix up to the first underscore plus the last four
    characters). Empty input maps to a stable placeholder.
    """
    if not token:
        return "***"
    last4 = token[-4:] if len(token) >= 4 else "*" * 4
    if "_" in token:
        prefix = token.split("_", 1)[0]
        return f"{prefix}_***{last4}"
    return f"***{last4}"


class CredentialStore:
    """Reads/writes the TOML credentials file with POSIX permission guards."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = Path(path) if path is not None else _default_config_dir() / _FILE_NAME

    @property
    def path(self) -> Path:
        return self._path

    # ── public API ──────────────────────────────────────────────────────────

    def verify_permissions(self) -> bool:
        """True iff the credential file mode is 0600 (POSIX only).

        Returns True on Windows where POSIX modes do not apply; the caller is
        expected to rely on per-user ACLs in that case.
        """
        if sys.platform == "win32":
            return True
        if not self._path.exists():
            return True
        actual = self._path.stat().st_mode & 0o777
        return actual == _FILE_MODE

    def get(self, service: str) -> str | None:
        self._guard_permissions_on_read()
        data = self._load()
        tokens = data.get(_TABLE_NAME, {})
        value = tokens.get(service)
        if value is not None:
            log.debug("loaded credential for service %s (%s)", service, mask_token(value))
        return value

    def set(self, service: str, token: str) -> None:
        if service not in SERVICE_TOKEN_PATTERNS:
            raise InvalidTokenFormatError(
                f"Unknown service {service!r}. Known services: {list(SUPPORTED_SERVICES)}"
            )
        if not SERVICE_TOKEN_PATTERNS[service].match(token):
            raise InvalidTokenFormatError(
                f"Token for service {service!r} does not match the expected format. "
                "See documentation for the canonical pattern."
            )
        self._ensure_parent_dir()
        if self._path.exists():
            self._guard_permissions_on_read()
        data = self._load()
        tokens = dict(data.get(_TABLE_NAME, {}))
        tokens[service] = token
        data[_TABLE_NAME] = tokens
        self._atomic_write(data)
        log.info("stored credential for service %s (%s)", service, mask_token(token))

    def delete(self, service: str) -> bool:
        if not self._path.exists():
            return False
        self._guard_permissions_on_read()
        data = self._load()
        tokens = dict(data.get(_TABLE_NAME, {}))
        if service not in tokens:
            return False
        tokens.pop(service)
        data[_TABLE_NAME] = tokens
        self._atomic_write(data)
        log.info("removed credential for service %s", service)
        return True

    def list_services(self) -> list[str]:
        """Return only the service names, never the token values."""
        if not self._path.exists():
            return []
        self._guard_permissions_on_read()
        data = self._load()
        return sorted(data.get(_TABLE_NAME, {}).keys())

    # ── internals ───────────────────────────────────────────────────────────

    def _guard_permissions_on_read(self) -> None:
        if not self.verify_permissions():
            raise InsecurePermissionsError(f"chmod 600 {self._path} to secure the file.")

    def _ensure_parent_dir(self) -> None:
        parent = self._path.parent
        parent.mkdir(parents=True, exist_ok=True)
        if sys.platform != "win32":
            try:
                parent.chmod(_DIR_MODE)
            except OSError as exc:  # pragma: no cover — defensive
                log.debug("could not tighten config dir mode: %s", exc)

    def _load(self) -> dict[str, dict[str, str]]:
        if not self._path.exists():
            return {}
        with open(self._path, "rb") as fh:
            raw = tomllib.load(fh)
        if _TABLE_NAME not in raw or not isinstance(raw[_TABLE_NAME], dict):
            raw[_TABLE_NAME] = {}
        return raw

    def _atomic_write(self, data: dict[str, dict[str, str]]) -> None:
        """Write ``data`` to disk with mode 0600 (POSIX).

        On POSIX, the file is created via ``os.open(O_CREAT|O_WRONLY|O_TRUNC,
        0o600)`` so the mode is set atomically — no observable window where the
        file exists with broader permissions. On Windows, ``Path.write_bytes``
        + ``chmod`` is used.
        """
        payload = tomli_w.dumps(data).encode("utf-8")
        if sys.platform == "win32":
            self._path.write_bytes(payload)
            return
        flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        fd = os.open(self._path, flags, _FILE_MODE)
        try:
            os.write(fd, payload)
        finally:
            os.close(fd)
        # Some umasks can drop bits from the create mode; chmod normalises.
        os.chmod(self._path, _FILE_MODE)


__all__ = [
    "SERVICE_TOKEN_PATTERNS",
    "SUPPORTED_SERVICES",
    "CredentialError",
    "CredentialStore",
    "InsecurePermissionsError",
    "InvalidTokenFormatError",
    "mask_token",
]
