"""
PUMA Understanding & Management w Agents.

Local, reproducible benchmarking of open LLMs on project management tasks.
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("puma-cp")
except PackageNotFoundError:  # bare source tree without an installed distribution
    __version__ = "0.0.0-unknown"
