#!/usr/bin/env python3
"""Create milestones, point labels and one issue per user story from docs/backlog.csv.

Dry run by default: prints what it would do. Run `--apply` from the repo root after
`gh auth login` and after filling scripts/handles.json. It never creates duplicates of an
issue whose title already exists.

The Iteration column is a GitHub Projects field: add an Iteration field to the Project by
hand and fill it from the CSV (the CLI cannot create it). Rubric reminder: stories must be
sized BEFORE the work starts, every item needs an assignee, milestone and iteration, and a
board filled in near the deadline scores Missing.
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path


def sh(cmd, apply, capture=False):
    print("  $", " ".join(cmd))
    if not apply:
        return ""
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 and "already_exists" not in res.stderr and "already exists" not in res.stderr:
        print(res.stderr.strip(), file=sys.stderr)
    return res.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backlog", default="docs/backlog.csv")
    a = ap.parse_args()
    handles = json.loads(Path("scripts/handles.json").read_text())
    if a.apply and any(v.startswith("REPLACE") for v in handles.values()):
        sys.exit("fill in scripts/handles.json first")
    rows = list(csv.DictReader(open(a.backlog, newline="")))
    existing = set()
    if a.apply:
        out = subprocess.run(["gh", "issue", "list", "--state", "all", "--limit", "500", "--json", "title"],
                             capture_output=True, text=True).stdout or "[]"
        existing = {i["title"] for i in json.loads(out)}
    for ms in sorted({r["milestone"] for r in rows}):
        sh(["gh", "api", "repos/:owner/:repo/milestones", "-f", "title=" + ms], a.apply)
    for pts in sorted({r["points"] for r in rows}, key=int):
        sh(["gh", "label", "create", "points:" + pts, "--force"], a.apply)
    for r in rows:
        title = "[%s] %s" % (r["id"], r["story"])
        if title in existing:
            print("skip (exists):", r["id"])
            continue
        body = ("**Acceptance:** %s\n\n**Story points:** %s\n**Iteration:** %s\n**Owner:** %s\n"
                % (r["acceptance"], r["points"], r["iteration"], r["owner"]))
        sh(["gh", "issue", "create", "--title", title, "--body", body, "--label", "points:" + r["points"],
            "--milestone", r["milestone"], "--assignee", handles[r["owner"]]], a.apply)
    if not a.apply:
        print("\n(dry run) add --apply to create these.")


if __name__ == "__main__":
    main()
