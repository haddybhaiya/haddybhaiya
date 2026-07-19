#!/usr/bin/env python3
"""
generate_terminal_graph.py

Builds a terminal-styled SVG showing a live `git log --graph` view of
recent public commit activity, pulled straight from the GitHub REST API.

Run daily by .github/workflows/terminal-graph.yml so the README always
shows fresh activity without any manual updates.
"""

import os
import random
import string
import requests
from datetime import datetime, timezone

USERNAME = os.environ.get("GH_USERNAME", "haddybhaiya")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUTPUT = "assets/terminal-graph.svg"
MAX_COMMITS = 10

HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def fetch_recent_commits():
    """Pull recent PushEvents from the user's public events feed."""
    url = f"https://api.github.com/users/{USERNAME}/events/public"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    events = resp.json()

    commits = []
    for event in events:
        if event.get("type") != "PushEvent":
            continue
        repo_name = event["repo"]["name"].split("/")[-1]
        for c in event["payload"].get("commits", []):
            commits.append({
                "sha": c["sha"][:7],
                "msg": c["message"].splitlines()[0][:48],
                "repo": repo_name,
            })
        if len(commits) >= MAX_COMMITS:
            break
    return commits[:MAX_COMMITS] or fallback_commits()


def fallback_commits():
    """Used when the feed has nothing fresh (rate limit, quiet day, etc)."""
    return [{
        "sha": "".join(random.choices(string.hexdigits.lower(), k=7)),
        "msg": "no fresh pushes yet -- check back tomorrow",
        "repo": "-",
    }]


def build_graph_lines(commits):
    lines = []
    for i, c in enumerate(commits):
        decoration = " (HEAD -> main)" if i == 0 else ""
        lines.append(f"* {c['sha']}{decoration} {c['msg']}")
        if i != len(commits) - 1:
            lines.append("|")
    return lines


def render_svg(lines, username):
    line_height = 22
    top_padding = 56
    width = 720
    height = top_padding + line_height * len(lines) + 30

    rows = ""
    for i, text in enumerate(lines):
        y = top_padding + i * line_height
        delay = round(i * 0.12, 2)
        color = "#7c3aed" if text.startswith("*") else "#3f3f46"
        safe_text = (text.replace("&", "&amp;")
                          .replace("<", "&lt;")
                          .replace(">", "&gt;"))
        rows += (f'<text x="24" y="{y}" fill="{color}" '
                 f'font-family="Fira Code, monospace" font-size="13" '
                 f'opacity="0"><animate attributeName="opacity" '
                 f'from="0" to="1" begin="{delay}s" dur="0.3s" '
                 f'fill="freeze"/>{safe_text}</text>\n')

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    svg = f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{width}" height="{height}" rx="10" fill="#0d1117"/>
  <rect width="{width}" height="32" rx="10" fill="#161b22"/>
  <rect y="16" width="{width}" height="16" fill="#161b22"/>
  <circle cx="20" cy="16" r="6" fill="#ff5f56"/>
  <circle cx="40" cy="16" r="6" fill="#ffbd2e"/>
  <circle cx="60" cy="16" r="6" fill="#27c93f"/>
  <text x="{width/2}" y="21" fill="#8b949e" font-family="Fira Code, monospace" font-size="12" text-anchor="middle">{username}@github: ~/activity</text>
  <text x="24" y="{top_padding - 22}" fill="#58a6ff" font-family="Fira Code, monospace" font-size="13">$ git log --oneline --graph --decorate -{len([l for l in lines if l.startswith('*')])}</text>
{rows}  <text x="24" y="{height - 10}" fill="#484f58" font-family="Fira Code, monospace" font-size="10">last updated {timestamp}</text>
</svg>'''
    return svg


def main():
    commits = fetch_recent_commits()
    lines = build_graph_lines(commits)
    svg = render_svg(lines, USERNAME)
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with open(OUTPUT, "w") as f:
        f.write(svg)
    print(f"Wrote {OUTPUT} with {len(commits)} commits")


if __name__ == "__main__":
    main()
