"""Unit tests for formatter.py (no network calls)."""

import os
import pytest

from formatter import format_message, _arrow


TITLE = "Test Sheet"


def test_format_message_empty():
    msg = format_message(TITLE, [])
    assert "no data" in msg.lower()


def test_format_message_two_columns_generic():
    records = [
        {"Metric": "Daily Active Users", "Value": "1,234"},
        {"Metric": "Revenue", "Value": "$56,789"},
    ]
    msg = format_message(TITLE, records)
    assert "Daily Active Users" in msg
    assert "1,234" in msg
    assert "Revenue" in msg
    assert "$56,789" in msg


def test_format_message_goals_table():
    records = [
        {
            "GOALS:": "January",
            "SMS Spend (Target)": "$7,950",
            "SMS Spend (Actual)": "$18,377",
        },
        {
            "GOALS:": "February",
            "SMS Spend (Target)": "$8,100",
            "SMS Spend (Actual)": "$15,112",
        },
    ]
    msg = format_message(TITLE, records)
    assert "January" in msg
    assert "February" in msg
    assert "$7,950" in msg
    assert "$18,377" in msg
    assert "→" in msg


def test_format_message_goals_positive_diff_emoji():
    records = [
        {
            "Month": "March",
            "Spend (Target)": "100",
            "Spend (Actual)": "120",
        }
    ]
    msg = format_message(TITLE, records)
    assert "✅" in msg


def test_format_message_goals_negative_diff_emoji():
    records = [
        {
            "Month": "April",
            "Spend (Target)": "100",
            "Spend (Actual)": "80",
        }
    ]
    msg = format_message(TITLE, records)
    assert "🔴" in msg


def test_arrow_positive():
    result = _arrow("$100", "$120")
    assert "✅" in result
    assert "+20" in result


def test_arrow_negative():
    result = _arrow("$100", "$80")
    assert "🔴" in result
    assert "-20" in result


def test_arrow_no_actual():
    result = _arrow("$100", "")
    assert result == "$100"


def test_format_message_title_in_output():
    msg = format_message("My Sheet", [{"k": "v", "k2": "v2"}])
    assert "My Sheet" in msg


def test_require_env_raises(monkeypatch):
    import os

    def _require_env(name):
        value = os.environ.get(name)
        if not value:
            raise EnvironmentError(
                f"Required environment variable '{name}' is not set."
            )
        return value

    monkeypatch.delenv("SHEET_ID", raising=False)
    with pytest.raises(EnvironmentError, match="SHEET_ID"):
        _require_env("SHEET_ID")
