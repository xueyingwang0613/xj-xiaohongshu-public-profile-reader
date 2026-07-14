#!/usr/bin/env python3
"""Read public data embedded in a Xiaohongshu profile HTML page."""

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from urllib.parse import urlparse


MARKER = "window.__INITIAL_STATE__="
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
)


class ReaderError(Exception):
    pass


def validate_url(url):
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https"):
        raise ReaderError("Profile URL must use http or https.")
    if host != "xiaohongshu.com" and not host.endswith(".xiaohongshu.com"):
        raise ReaderError("Only public xiaohongshu.com profile URLs are supported.")
    if not parsed.path.startswith("/user/profile/"):
        raise ReaderError("Expected a public URL with path /user/profile/<user-id>.")


def fetch_html(url, timeout):
    validate_url(url)
    if not shutil.which("curl"):
        raise ReaderError("curl is required to fetch the public profile page.")
    command = [
        "curl",
        "-sS",
        "-L",
        "--compressed",
        "--max-time",
        str(timeout),
        "-A",
        USER_AGENT,
        url,
    ]
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ReaderError("Failed to start curl: %s" % exc)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise ReaderError("Failed to fetch public profile: %s" % (detail or "curl error"))
    if not result.stdout:
        raise ReaderError("The public profile response was empty.")
    return result.stdout.decode("utf-8", "replace")


def extract_object(html):
    marker_index = html.find(MARKER)
    if marker_index < 0:
        raise ReaderError(
            "The public page did not include window.__INITIAL_STATE__; "
            "the page format or access response may have changed."
        )
    start = html.find("{", marker_index + len(MARKER))
    if start < 0:
        raise ReaderError("The embedded public state did not contain a JSON object.")

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(html)):
        char = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return html[start : index + 1]
    raise ReaderError("The embedded public state was incomplete.")


def normalize_undefined(payload):
    output = []
    index = 0
    in_string = False
    escaped = False
    token = "undefined"
    while index < len(payload):
        char = payload[index]
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if payload.startswith(token, index):
            before = payload[index - 1] if index else ""
            after_index = index + len(token)
            after = payload[after_index] if after_index < len(payload) else ""
            if not (before.isalnum() or before in "_$") and not (
                after.isalnum() or after in "_$"
            ):
                output.append("null")
                index = after_index
                continue
        output.append(char)
        index += 1
    return "".join(output)


def parse_state(html):
    payload = normalize_undefined(extract_object(html))
    try:
        return json.loads(payload)
    except ValueError as exc:
        raise ReaderError("Could not parse the embedded public state: %s" % exc)


def normalize_profile(state, source_url, max_notes):
    user = state.get("user") or {}
    page = user.get("userPageData") or {}
    result = page.get("result") or {}
    if result and not result.get("success", False):
        raise ReaderError("The public profile response was not successful.")

    basic = page.get("basicInfo") or {}
    note_tabs = user.get("notes") or []
    first_tab = note_tabs[0] if note_tabs and isinstance(note_tabs[0], list) else []
    notes = []
    for item in first_tab[:max_notes]:
        card = item.get("noteCard") or {}
        interaction = card.get("interactInfo") or {}
        cover = card.get("cover") or {}
        notes.append(
            {
                "index": item.get("index"),
                "title": card.get("displayTitle") or "",
                "type": card.get("type") or "",
                "like_count_display": interaction.get("likedCount") or "",
                "sticky": bool(interaction.get("sticky", False)),
                "cover": {
                    "url": cover.get("urlDefault") or cover.get("urlPre") or "",
                    "width": cover.get("width"),
                    "height": cover.get("height"),
                },
            }
        )

    interactions = {}
    for entry in page.get("interactions") or []:
        key = entry.get("type") or entry.get("name")
        if key:
            interactions[key] = {
                "label": entry.get("name") or "",
                "display": entry.get("count") or entry.get("i18nCount") or "",
            }

    return {
        "source_url": source_url or "",
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_type": "public_webpage_snapshot",
        "profile": {
            "user_id": basic.get("redId") or "",
            "nickname": basic.get("nickname") or "",
            "description": basic.get("desc") or "",
            "ip_location": basic.get("ipLocation") or "",
            "avatar_url": basic.get("imageb") or basic.get("images") or "",
            "tags": page.get("tags") or [],
            "interaction_counts": interactions,
        },
        "notes": notes,
        "limitations": [
            "Displayed counts may be rounded, hidden, or empty.",
            "Notes are limited to the public first-page snapshot.",
            "Private creator analytics, messages, drafts, and conversion data are not accessed.",
        ],
    }


def build_parser():
    parser = argparse.ArgumentParser(
        description="Read structured data from a public Xiaohongshu profile page."
    )
    parser.add_argument("url", nargs="?", help="Public Xiaohongshu profile URL")
    parser.add_argument("--html-file", help="Parse an already-downloaded HTML file")
    parser.add_argument("--source-url", help="Source URL to record when using --html-file")
    parser.add_argument("--max-notes", type=int, default=30)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--output", help="Write JSON to this file instead of stdout")
    return parser


def main():
    args = build_parser().parse_args()
    if bool(args.url) == bool(args.html_file):
        raise ReaderError("Provide either a profile URL or --html-file, but not both.")
    if args.max_notes < 0:
        raise ReaderError("--max-notes must be zero or greater.")
    if args.timeout <= 0:
        raise ReaderError("--timeout must be greater than zero.")

    if args.html_file:
        if not os.path.isfile(args.html_file):
            raise ReaderError("HTML file not found: %s" % args.html_file)
        with open(args.html_file, "r", encoding="utf-8") as handle:
            html = handle.read()
        source_url = args.source_url or ""
        if source_url:
            validate_url(source_url)
    else:
        source_url = args.url
        html = fetch_html(args.url, args.timeout)

    data = normalize_profile(parse_state(html), source_url, args.max_notes)
    serialized = json.dumps(
        data,
        ensure_ascii=False,
        indent=2 if args.pretty else None,
        sort_keys=False,
    )
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.write("\n")
    else:
        sys.stdout.write(serialized)
        sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        main()
    except ReaderError as exc:
        sys.stderr.write("Error: %s\n" % exc)
        sys.exit(2)
