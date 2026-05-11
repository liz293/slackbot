"""Pure formatting logic — no third-party imports, easy to unit-test."""


def format_message(records: list[dict]) -> str:
    """Turn sheet rows into a readable Slack message."""
    if not records:
        return "*Metrics update:* no data found in the sheet."

    lines = ["*📊 Metrics Update*", ""]

    headers = list(records[0].keys())

    if len(headers) == 2:
        key_col, val_col = headers
        for row in records:
            lines.append(f"• *{row[key_col]}:* {row[val_col]}")
    else:
        for i, row in enumerate(records, start=1):
            parts = "  |  ".join(f"*{k}:* {v}" for k, v in row.items())
            lines.append(f"{i}. {parts}")

    return "\n".join(lines)
