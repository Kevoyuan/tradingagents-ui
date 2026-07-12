"""Tests for app.py helper functions (non-Streamlit parts)."""

from __future__ import annotations


def test_safe_report_filename_part_basic():
    from app import safe_report_filename_part
    assert safe_report_filename_part("gpt-4") == "gpt-4"


def test_safe_report_filename_part_special_chars():
    from app import safe_report_filename_part
    result = safe_report_filename_part("openai/gpt-4-turbo")
    assert "/" not in result
    assert "gpt-4-turbo" in result


def test_safe_report_filename_part_empty():
    from app import safe_report_filename_part
    assert safe_report_filename_part("") == "unknown"


def test_safe_report_filename_part_none():
    from app import safe_report_filename_part
    assert safe_report_filename_part(None) == "unknown"  # type: ignore[arg-type]


def test_safe_report_filename_part_long():
    from app import safe_report_filename_part
    result = safe_report_filename_part("a" * 200)
    assert len(result) <= 80


def test_safe_report_filename_part_whitespace_only():
    from app import safe_report_filename_part
    result = safe_report_filename_part("   ")
    assert result == "unknown"


def test_safe_report_filename_part_consecutive_dashes():
    from app import safe_report_filename_part
    result = safe_report_filename_part("a---b")
    assert "--" not in result


def test_safe_report_filename_part_preserves_dots():
    from app import safe_report_filename_part
    result = safe_report_filename_part("model.v2.1")
    assert "." in result


def test_setup_path_for_desktop_app():
    import os

    from app import setup_path_for_desktop_app

    original_path = os.environ.get("PATH", "")
    try:
        setup_path_for_desktop_app()
        current_path = os.environ.get("PATH", "")
        assert "/usr/bin" in current_path or len(current_path) > 0
    finally:
        os.environ["PATH"] = original_path


def test_get_bun_command():
    from app import get_bun_command

    try:
        cmd = get_bun_command()
        assert len(cmd) > 0
        assert cmd[0] in ("bun", "npx")
    except RuntimeError as exc:
        assert "Generate HTML requires" in str(exc)
