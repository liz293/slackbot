"""Pure formatting logic — no third-party imports, easy to unit-test."""

import re

# Column names that contain a metric value to be highlighted as "target"
_TARGET_SUFFIX = "(target)"
_ACTUAL_SUFFIX = "(actual)"

# Months we recognise as the first-column label in the goals table
_MONTH_NAMES = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
}


def _is_month_row(row: dict) -> bool:
    first = next(iter(row.values()), "").strip().lower()
    return first in _MONTH_NAMES


def _arrow(target: str, actual: str) -> str:
    """Return 'target → actual (±diff)' with a pass/fail emoji when both are numeric."""
    def parse(s: str) -> float | None:
        cleaned = re.sub(r"[$,]", "", s.strip())
        try:
            return float(cleaned)
        except ValueError:
            return None

    t, a = parse(target), parse(actual)
    if t is not None and a is not None and t != 0:
        diff = a - t
        sign = "+" if diff >= 0 else ""
        icon = "✅" if diff >= 0 else "🔴"
        return f"{target} → {actual} ({sign}{diff:,.0f}) {icon}"
    if actual:
        return f"{target} → {actual}"
    return target  # actual not yet available


def _pair_target_actual(headers: list[str]) -> list[tuple[str, str | None]]:
    """Group headers into (metric_base, actual_header | None) pairs for display."""
    paired: list[tuple[str, str | None]] = []
    skip: set[str] = set()
    for h in headers:
        if h in skip:
            continue
        lower = h.lower()
        if lower.endswith(_TARGET_SUFFIX):
            base = h[: -len(_TARGET_SUFFIX)].strip()
            # Look for a matching actual column
            actual_h = next(
                (x for x in headers if x.lower() == f"{base.lower()} {_ACTUAL_SUFFIX}"),
                None,
            )
            if actual_h:
                skip.add(actual_h)
            paired.append((h, actual_h))
        elif lower.endswith(_ACTUAL_SUFFIX):
            paired.append((h, None))
        else:
            paired.append((h, None))
    return paired


def _format_goals_table(title: str, month_rows: list[dict]) -> str:
    if not month_rows:
        return f"*{title}*\n_No monthly data found._"

    headers = list(month_rows[0].keys())
    month_col = headers[0]
    metric_headers = headers[1:]

    pairs = _pair_target_actual(metric_headers)

    lines = [f"*📊 {title}*", ""]

    for row in month_rows:
        month = row[month_col]
        parts: list[str] = []
        skip: set[str] = set()
        for target_h, actual_h in pairs:
            if target_h in skip:
                continue
            t_lower = target_h.lower()
            if actual_h and t_lower.endswith(_TARGET_SUFFIX):
                base = target_h[: -len(_TARGET_SUFFIX)].strip()
                val = _arrow(row.get(target_h, ""), row.get(actual_h, ""))
                parts.append(f"*{base}:* {val}")
                skip.add(actual_h)
            else:
                v = row.get(target_h, "")
                if v:
                    parts.append(f"*{target_h}:* {v}")

        if parts:
            lines.append(f"*{month}*")
            for p in parts:
                lines.append(f"  • {p}")

    return "\n".join(lines)


def _format_generic(title: str, records: list[dict]) -> str:
    if not records:
        return f"*{title}*\n_No data found._"

    lines = [f"*📊 {title}*", ""]
    headers = list(records[0].keys())

    if len(headers) == 2:
        k, v = headers
        for row in records:
            lines.append(f"• *{row[k]}:* {row[v]}")
    else:
        for i, row in enumerate(records, start=1):
            parts = "  |  ".join(f"*{k}:* {v}" for k, v in row.items() if v)
            if parts:
                lines.append(f"{i}. {parts}")

    return "\n".join(lines)


def format_message(title: str, records: list[dict]) -> str:
    """Turn sheet rows into a readable Slack message.

    If the first column contains month names the sheet is treated as a
    goals/targets table and rendered with target→actual comparisons.
    Otherwise a generic key-value layout is used.
    """
    if not records:
        return f"*{title}*\n_No data found in the sheet._"

    month_rows = [r for r in records if _is_month_row(r)]
    if month_rows:
        # Keep only the first occurrence of each month (the goals table).
        # The same month names reappear lower in the sheet for campaign breakdowns.
        seen: set[str] = set()
        deduped: list[dict] = []
        for r in month_rows:
            key = next(iter(r.values())).strip().lower()
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        return _format_goals_table(title, deduped)

    return _format_generic(title, records)
