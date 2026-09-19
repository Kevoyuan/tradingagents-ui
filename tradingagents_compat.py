"""TradingAgents version and install compatibility helpers."""

from __future__ import annotations

import importlib.metadata
import re
from dataclasses import dataclass

TRADINGAGENTS_REPO_URL = "https://github.com/TauricResearch/TradingAgents.git"
TRADINGAGENTS_TARGET_TAG = "v0.5.0"
TRADINGAGENTS_MIN_VERSION = (0, 5, 0)
TRADINGAGENTS_MAX_VERSION = (0, 6, 0)


def supported_range() -> str:
    """Render the supported range from the constants so it cannot drift.

    Public because other modules surface the same string to the user; deriving
    it in one place is what keeps a version bump from leaving stale copy behind.
    """
    lo = ".".join(str(part) for part in TRADINGAGENTS_MIN_VERSION)
    hi = ".".join(str(part) for part in TRADINGAGENTS_MAX_VERSION)
    return f">={lo},<{hi}"


def ui_version() -> str:
    """Read the UI package version from installed package metadata."""
    try:
        return importlib.metadata.version("tradingagents-ui")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def version_tuple(value: str) -> tuple[int, int, int] | None:
    match = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", value.strip())
    return tuple(map(int, match.groups())) if match else None


@dataclass(frozen=True)
class CompatibilityStatus:
    installed_version: str
    compatible: bool
    message: str


def tradingagents_compatibility(version: str | None = None) -> CompatibilityStatus:
    if version is None:
        try:
            version = importlib.metadata.version("tradingagents")
        except importlib.metadata.PackageNotFoundError:
            return CompatibilityStatus(
                "missing", False, f"TradingAgents is not installed. Install {supported_range()}."
            )

    parsed = version_tuple(version)
    if parsed is None:
        return CompatibilityStatus(
            version, False, f"Cannot verify TradingAgents version {version!r}. Expected {supported_range()}."
        )
    if parsed < TRADINGAGENTS_MIN_VERSION:
        return CompatibilityStatus(
            version,
            False,
            f"TradingAgents {version} is too old. Install {TRADINGAGENTS_TARGET_TAG}.",
        )
    if parsed >= TRADINGAGENTS_MAX_VERSION:
        return CompatibilityStatus(
            version, False, f"TradingAgents {version} is not supported yet. This UI supports {supported_range()}."
        )
    return CompatibilityStatus(version, True, f"TradingAgents {version} is compatible.")


def tagged_install_requirement(tag: str = TRADINGAGENTS_TARGET_TAG) -> str:
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError(f"Invalid TradingAgents release tag: {tag}")
    return f"git+{TRADINGAGENTS_REPO_URL}@{tag}"
