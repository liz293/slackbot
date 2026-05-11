"""
sheets_to_slack.py — reads metrics from a Google Sheet and posts them to Slack on a schedule.

Required env vars:
    GOOGLE_CREDENTIALS_JSON   Service account JSON (single-line string)
    SHEET_ID                  Google Sheet ID
    SLACK_BOT_TOKEN           Slack Bot OAuth token (xoxb-...)
    SLACK_CHANNEL             Channel name or ID to post to

Optional env vars:
    WORKSHEET_NAME            Worksheet tab name (takes priority over GID)
    WORKSHEET_GID             Worksheet numeric GID from the URL (e.g. 768021914)
                              Falls back to the first tab if neither is set.
    SCHEDULE_INTERVAL_MINUTES How often to post in minutes (default: 60)
"""

import json
import logging
import os
import time

import gspread
import schedule
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from formatter import format_message

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(f"Required environment variable '{name}' is not set.")
    return value


def build_sheets_client() -> gspread.Client:
    raw = _require_env("GOOGLE_CREDENTIALS_JSON")
    info = json.loads(raw)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _find_worksheet(spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet:
    """Resolve the target worksheet by name, GID, or index 0 (in that priority)."""
    name = os.environ.get("WORKSHEET_NAME")
    if name:
        return spreadsheet.worksheet(name)

    gid = os.environ.get("WORKSHEET_GID")
    if gid:
        gid_int = int(gid)
        for ws in spreadsheet.worksheets():
            if ws.id == gid_int:
                return ws
        raise ValueError(f"No worksheet with GID {gid} found in spreadsheet.")

    return spreadsheet.get_worksheet(0)


def read_metrics(client: gspread.Client) -> tuple[str, list[dict]]:
    """Return (worksheet_title, rows) using raw values to handle duplicate/empty headers.

    Columns with blank headers are skipped (they're visual spacers in the sheet).
    Duplicate header names get a numeric suffix (_2, _3, …).
    Only rows that have at least one non-empty cell are returned.
    """
    sheet_id = _require_env("SHEET_ID")

    spreadsheet = client.open_by_key(sheet_id)
    ws = _find_worksheet(spreadsheet)

    all_values = ws.get_all_values()
    if not all_values:
        return ws.title, []

    raw_headers = all_values[0]

    # Columns whose header is blank are spacers — skip them entirely.
    active_cols = [i for i, h in enumerate(raw_headers) if h.strip()]

    # Deduplicate: "SMS Spend" appearing twice → "SMS Spend", "SMS Spend_2"
    seen: dict[str, int] = {}
    headers: list[str] = []
    for i in active_cols:
        h = raw_headers[i]
        count = seen.get(h, 0) + 1
        seen[h] = count
        headers.append(h if count == 1 else f"{h}_{count}")

    records: list[dict] = []
    for row in all_values[1:]:
        padded = row + [""] * max(0, len(raw_headers) - len(row))
        values = [padded[i] for i in active_cols]
        if any(v.strip() for v in values):
            records.append(dict(zip(headers, values)))

    log.info("Read %d row(s) from worksheet '%s'.", len(records), ws.title)
    return ws.title, records



def post_to_slack(client: WebClient, message: str) -> None:
    channel = _require_env("SLACK_CHANNEL")
    try:
        response = client.chat_postMessage(channel=channel, text=message, mrkdwn=True)
        log.info("Message posted to %s (ts=%s).", channel, response["ts"])
    except SlackApiError as exc:
        log.error("Slack API error: %s", exc.response["error"])
        raise


def run_once(sheets_client: gspread.Client, slack_client: WebClient) -> None:
    log.info("Fetching metrics from Google Sheets…")
    title, records = read_metrics(sheets_client)
    message = format_message(title, records)
    log.info("Posting to Slack…")
    post_to_slack(slack_client, message)
    log.info("Done.")


def main() -> None:
    interval = int(os.environ.get("SCHEDULE_INTERVAL_MINUTES", "60"))

    sheets_client = build_sheets_client()
    slack_client = WebClient(token=_require_env("SLACK_BOT_TOKEN"))

    log.info("Starting — will post every %d minute(s).", interval)

    # Post immediately on startup, then on schedule.
    run_once(sheets_client, slack_client)

    schedule.every(interval).minutes.do(run_once, sheets_client, slack_client)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
