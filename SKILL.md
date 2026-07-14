---
name: xj-xiaohongshu-public-profile-reader
description: Read and structure data exposed by a public Xiaohongshu/RedNote user profile page, including public profile fields, displayed interaction counts, first-page note titles, likes, types, sticky flags, and cover metadata. Use when a user provides a Xiaohongshu public profile URL and asks to read, export, inspect, summarize, audit, or prepare the account data for downstream analysis. Do not use for login-only pages, private analytics, messages, drafts, or actions that modify an account.
---

# Xiaohongshu Public Profile Reader

Read only information already embedded in a public Xiaohongshu profile page. Do not log in, use cookies, call private APIs, bypass access controls, or claim access to creator analytics.

## Read a profile

Run the bundled parser with the public profile URL:

```bash
python3 <skill-dir>/scripts/read_profile.py "https://www.xiaohongshu.com/user/profile/<user-id>" --pretty
```

The script invokes `curl`, follows public redirects, extracts `window.__INITIAL_STATE__`, and emits normalized JSON. Request network approval when the environment requires it.

To parse an already-downloaded page without network access:

```bash
python3 <skill-dir>/scripts/read_profile.py --html-file /path/to/profile.html --source-url "https://www.xiaohongshu.com/user/profile/<user-id>" --pretty
```

Use `--output /path/to/result.json` only when the user asks for a saved export. Use `--max-notes N` to limit the first public notes tab.

## Interpret the result

- Treat `interaction_counts` and `like_count_display` as display strings, not exact analytics. Values may be rounded, hidden, or empty.
- Treat `notes` as the public first-page snapshot, not the full account history.
- Use `fetched_at` to state when the snapshot was collected.
- Do not infer impressions, click-through rate, saves, completion rate, follower conversion, or revenue.
- Do not expose anti-abuse tokens or raw page state. The parser intentionally omits them.

## Visual inspection

When the user requests a visual or cover audit, select four to six representative `cover.url` values rather than downloading every cover. Include recent posts, high-interaction posts, and distinct content categories. Download only those public images, inspect them with the available image viewer, and distinguish direct visual observations from performance inferences.

## Failure handling

- If the URL is not a public Xiaohongshu profile URL, stop and request the correct URL.
- If the page lacks `window.__INITIAL_STATE__`, report that the public page format or access response changed; do not switch to private endpoints.
- If public data is insufficient, ask for screenshots or creator-center exports supplied by the user.

## Response boundary

State that the result comes from a public webpage snapshot. Clearly separate public observations from recommendations produced by another analysis skill.
