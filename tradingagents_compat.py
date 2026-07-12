"""TradingAgents version and install compatibility helpers."""

from __future__ import annotations

import importlib.metadata
import re
from dataclasses import dataclass

TRADINGAGENTS_REPO_URL = "https://github.com/TauricResearch/TradingAgents.git"
TRADINGAGENTS_TARGET_TAG = "v0.3.1"
TRADINGAGENTS_MIN_VERSION = (0, 3, 1)
TRADINGAGENTS_MAX_VERSION = (0, 4, 0)


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
                "missing", False, "TradingAgents is not installed. Install compatible version v0.3.1."
            )

    parsed = version_tuple(version)
    if parsed is None:
        return CompatibilityStatus(
            version, False, f"Cannot verify TradingAgents version {version!r}. Expected >=0.3.1,<0.4."
        )
    if parsed < TRADINGAGENTS_MIN_VERSION:
        return CompatibilityStatus(version, False, f"TradingAgents {version} is too old. Install v0.3.1.")
    if parsed >= TRADINGAGENTS_MAX_VERSION:
        return CompatibilityStatus(
            version, False, f"TradingAgents {version} is not supported yet. This UI supports >=0.3.1,<0.4."
        )
    return CompatibilityStatus(version, True, f"TradingAgents {version} is compatible.")


def tagged_install_requirement(tag: str = TRADINGAGENTS_TARGET_TAG) -> str:
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError(f"Invalid TradingAgents release tag: {tag}")
    return f"git+{TRADINGAGENTS_REPO_URL}@{tag}"
