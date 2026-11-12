#!/usr/bin/env python3
"""Make the GitHub issues and milestones match docs/backlog.csv after stories were renamed.

Issues are matched to backlog rows by the story sentence, so a changed story ID is picked up.
For each match it fixes the title "[ID] story" and the body. It also renames milestones listed
in RENAMED_MILESTONES. Dry run by default: add --apply to do it. Run from the repo root.
"""
import argparse
import csv
import json
import re
import subprocess
import sys

RENAMED_MILESTONES = {"M1 Setup and proposal evidence": "M1 Environment setup"}


def gh(args):
    res = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if res.returncode != 0:
        print("  FAILED:", res.stderr.strip(), file=sys.stderr)
    return res.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--backlog", default="docs/backlog.csv")
    a = ap.parse_args()
    by_story = {r["story"]: r for r in csv.DictReader(open(a.backlog, newline=""))}
    changes = 0
    for ms in json.loads(gh(["api", "repos/:owner/:repo/milestones?state=all"]) or "[]"):
        new = RENAMED_MILESTONES.get(ms["title"])
        if new:
            print("rename milestone '%s' -> '%s'" % (ms["title"], new))
            changes += 1
            if a.apply:
                gh(["api", "-X", "PATCH", "repos/:owner/:repo/milestones/%d" % ms["number"], "-f", "title=" + new])
    issues = json.loads(gh(["issue", "list", "--state", "all", "--limit", "500", "--json", "number,title,body"]) or "[]")
    seen = set()
    for issue in sorted(issues, key=lambda i: i["number"]):
        m = re.match(r"\[(M\d-\d\d)\] (.*)$", issue["title"], re.S)
        if not m:
            continue
        r = by_story.get(m.group(2))
        if r is None:
            print("no backlog row for #%d %s (left alone)" % (issue["number"], issue["title"][:60]))
            continue
        seen.add(r["id"])
        title = "[%s] %s" % (r["id"], r["story"])
        body = ("**Acceptance:** %s\n\n**Story points:** %s\n**Iteration:** %s\n**Owner:** %s\n"
                % (r["acceptance"], r["points"], r["iteration"], r["owner"]))
        if title != issue["title"] or body.strip() != (issue["body"] or "").strip():
            what = "%s -> %s" % (m.group(1), r["id"]) if title != issue["title"] else "[%s] body" % r["id"]
            print("update #%d %s" % (issue["number"], what))
            changes += 1
            if a.apply:
                gh(["issue", "edit", str(issue["number"]), "--title", title, "--body", body])
    missing = sorted(r["id"] for r in by_story.values() if r["id"] not in seen)
    if missing:
        print("backlog stories with no issue:", ", ".join(missing))
    print("\n%d change(s), %d stories in the backlog." % (changes, len(by_story)))
    if not a.apply:
        print("(dry run) add --apply to do it.")


if __name__ == "__main__":
    main()
