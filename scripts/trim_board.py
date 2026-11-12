#!/usr/bin/env python3
"""Bring the GitHub issues in line with docs/backlog.csv after the backlog was trimmed.

Deletes the issue of every story that is no longer in the CSV and rewrites the body of every
remaining issue whose acceptance text changed. Dry run by default: add --apply to do it.
Deleting an issue is permanent. Run from the repo root.
"""
import argparse
import csv
import json
import re
import subprocess
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backlog", default="docs/backlog.csv")
    a = ap.parse_args()
    rows = {r["id"]: r for r in csv.DictReader(open(a.backlog, newline=""))}
    out = subprocess.run(["gh", "issue", "list", "--state", "all", "--limit", "500", "--json", "number,title,body"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(out.stderr.strip())
    deleted = updated = 0
    for issue in sorted(json.loads(out.stdout), key=lambda i: i["number"]):
        m = re.match(r"\[(M\d-\d\d)\] ", issue["title"])
        if not m:
            continue
        sid, num = m.group(1), str(issue["number"])
        if sid not in rows:
            print("delete #%s %s" % (num, issue["title"][:70]))
            deleted += 1
            if a.apply:
                res = subprocess.run(["gh", "issue", "delete", num, "--yes"], capture_output=True, text=True)
                if res.returncode != 0:
                    print("  FAILED:", res.stderr.strip(), file=sys.stderr)
            continue
        r = rows[sid]
        body = ("**Acceptance:** %s\n\n**Story points:** %s\n**Iteration:** %s\n**Owner:** %s\n"
                % (r["acceptance"], r["points"], r["iteration"], r["owner"]))
        if body.strip() != (issue["body"] or "").strip():
            print("update #%s [%s] acceptance text" % (num, sid))
            updated += 1
            if a.apply:
                res = subprocess.run(["gh", "issue", "edit", num, "--body", body], capture_output=True, text=True)
                if res.returncode != 0:
                    print("  FAILED:", res.stderr.strip(), file=sys.stderr)
    print("\n%d to delete, %d to update, %d stories in the backlog." % (deleted, updated, len(rows)))
    if not a.apply:
        print("(dry run) add --apply to do it.")


if __name__ == "__main__":
    main()
