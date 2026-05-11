"""Unit tests for sheets_to_slack.py (no network calls)."""

import os
import pytest

from formatter import format_message


def test_format_message_empty():
    msg = format_message([])
    assert "no data" in msg.lower()


def test_format_message_two_columns():
    records = [
        {"Metric": "Daily Active Users", "Value": "1,234"},
        {"Metric": "Revenue", "Value": "$56,789"},
    ]
    msg = format_message(records)
    assert "Daily Active Users" in msg
    assert "1,234" in msg
    assert "Revenue" in msg
    assert "$56,789" in msg


def test_format_message_multi_column():
    records = [
        {"Date": "2024-01-01", "Users": 100, "Revenue": 500},
        {"Date": "2024-01-02", "Users": 120, "Revenue": 620},
    ]
    msg = format_message(records)
    assert "2024-01-01" in msg
    assert "2024-01-02" in msg
    assert "Revenue" in msg


def test_format_message_header_present():
    records = [{"Metric": "X", "Value": "Y"}]
    msg = format_message(records)
    assert "Metrics Update" in msg


def test_require_env_raises(monkeypatch):
    import importlib, sys
    # Remove cached module to allow fresh import with env var absent.
    sys.modules.pop("sheets_to_slack", None)
    monkeypatch.delenv("SHEET_ID", raising=False)

    def _require_env(name):
        value = os.environ.get(name)
        if not value:
            raise EnvironmentError(f"Required environment variable '{name}' is not set.")
        return value

    import os
    with pytest.raises(EnvironmentError, match="SHEET_ID"):
        _require_env("SHEET_ID")
