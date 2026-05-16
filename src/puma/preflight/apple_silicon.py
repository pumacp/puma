"""Apple Silicon detection for PUMA profile selection.

This module is platform-isolated: all macOS-specific subprocess calls
(``sysctl``) are wrapped in functions that can be mocked from tests on
non-macOS systems. On Linux, every public entry point returns ``None``
without invoking subprocess, so the module is safe to import from
anywhere in the codebase and from CI runners that have no Mac
hardware.

The detection chain is:

  is_apple_silicon()        — platform.system()/machine() gate
  └─> get_chip_brand()      — sysctl machdep.cpu.brand_string
  └─> get_unified_memory_gb()  — sysctl hw.memsize / 1024**3
  └─> detect_apple_silicon_profile()  — chip brand → profile identifier

``detect_apple_silicon_profile`` returns one of the 9 v2.6.0 profile
identifiers (``apple-silicon-m3``, ``-m3-pro``, ``-m3-max``, ``-m4``,
``-m4-pro``, ``-m4-max``, ``-m5``, ``-m5-pro``, ``-m5-max``,
``-m5-ultra``) or ``None`` if the chip brand is unrecognised
(forward-compat for future M-series variants we have not yet
catalogued).

Empirical validation of every apple-silicon-* profile is deferred to
a future Sprint when Mac hardware becomes available to the project;
see ``docs/CROSS_ARCH_REPRODUCIBILITY.md``.
"""

from __future__ import annotations

import platform
import subprocess

CHIP_BRAND_TO_PROFILE: dict[str, str] = {
    "Apple M3": "apple-silicon-m3",
    "Apple M3 Pro": "apple-silicon-m3-pro",
    "Apple M3 Max": "apple-silicon-m3-max",
    "Apple M4": "apple-silicon-m4",
    "Apple M4 Pro": "apple-silicon-m4-pro",
    "Apple M4 Max": "apple-silicon-m4-max",
    "Apple M5": "apple-silicon-m5",
    "Apple M5 Pro": "apple-silicon-m5-pro",
    "Apple M5 Max": "apple-silicon-m5-max",
    "Apple M5 Ultra": "apple-silicon-m5-ultra",
}


def is_apple_silicon() -> bool:
    """Return True iff running on macOS arm64."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def get_chip_brand() -> str | None:
    """Return the chip brand string from ``sysctl``.

    Returns ``None`` on non-macOS hosts, on subprocess failure, or when
    sysctl is missing. The returned string is exactly what sysctl emits
    (e.g. ``"Apple M4 Pro"``).
    """
    if not is_apple_silicon():
        return None
    try:
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
    ):
        return None


def get_unified_memory_gb() -> int | None:
    """Return unified memory size in whole GB from ``sysctl hw.memsize``.

    Returns ``None`` on non-macOS hosts or on any subprocess/parse
    failure. The conversion uses integer division by ``1024**3`` (GiB).
    """
    if not is_apple_silicon():
        return None
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return int(result.stdout.strip()) // (1024**3)
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
        ValueError,
    ):
        return None


def detect_apple_silicon_profile() -> str | None:
    """Map the detected chip brand to a PUMA profile identifier.

    Returns one of the apple-silicon-* identifiers in
    ``CHIP_BRAND_TO_PROFILE``, or ``None`` if:

    - The host is not macOS arm64.
    - ``sysctl`` is unavailable or fails.
    - The chip brand is recognised by sysctl but not yet catalogued
      here (e.g. a future M6 family). The caller is expected to fall
      through to the existing CPU/GPU dispatch in that case.
    """
    brand = get_chip_brand()
    if brand is None:
        return None
    return CHIP_BRAND_TO_PROFILE.get(brand)


def get_apple_silicon_info() -> dict[str, str | int | None] | None:
    """Return full diagnostic info for ``puma profile`` output.

    Returns ``None`` if not on Apple Silicon. Otherwise returns a dict
    with ``chip_brand``, ``profile``, ``unified_memory_gb``, and
    ``platform`` — useful for the CLI's diagnostic display even when
    the chip variant is not yet mapped (``profile`` will be ``None``
    in that case).
    """
    if not is_apple_silicon():
        return None
    return {
        "chip_brand": get_chip_brand(),
        "profile": detect_apple_silicon_profile(),
        "unified_memory_gb": get_unified_memory_gb(),
        "platform": platform.platform(),
    }
