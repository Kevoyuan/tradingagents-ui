"""Safe, scoped environment handling for a single TradingAgents run."""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager


def effective_environment(
    names: tuple[str, ...],
    sidebar_values: Mapping[str, str],
    secret_values: Mapping[str, str],
    process_environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Resolve credentials in sidebar > secrets > process environment order."""
    process_environment = process_environment or os.environ
    resolved: dict[str, str] = {}
    for name in names:
        value = sidebar_values.get(name) or secret_values.get(name) or process_environment.get(name)
        if value:
            resolved[name] = str(value)
    return resolved


@contextmanager
def temporary_environment(overrides: Mapping[str, str]) -> Iterator[None]:
    """Apply non-empty values for one run and restore the exact previous state."""
    previous: dict[str, str | None] = {}
    try:
        for name, value in overrides.items():
            if not value:
                continue
            previous[name] = os.environ.get(name)
            os.environ[name] = value
        yield
    finally:
        for name, old_value in previous.items():
            if old_value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = old_value
