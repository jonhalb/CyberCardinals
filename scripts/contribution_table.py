#!/usr/bin/env python3
"""Individual Contribution Summary Table from docs/backlog.csv.

The rubric computes each member's grade from story points earned divided by the team total,
verified against the board and the commit history. docs/backlog.csv mirrors the board: keep
`status` in step with the Project board (done / in_progress / todo), and keep the board the
source of truth.

    python scripts/contribution_table.py                      # print the table
    python scripts/contribution_table.py --git                # add commit counts from git history
    python scripts/contribution_table.py --write-readme README.md
"""
import argparse
import csv
import subprocess
from collections import OrderedDict
from pathlib import Path

START, END = "<!-- CONTRIB:START -->", "<!-- CONTRIB:END -->"


def load(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def summarize(rows):
    out = OrderedDict()
    for r in rows:
        m = out.setdefault(r["owner"], {"done": 0, "earned": 0, "planned": 0})
        pts = int(r["points"])
        m["planned"] += pts
        if r["status"].strip().lower() == "done":
            m["done"] += 1
            m["earned"] += pts
    return out


def commit_counts(names):
    try:
        text = subprocess.run(["git", "shortlog", "-sn", "--all", "--no-merges"], capture_output=True,
                              text=True, check=True).stdout
    except Exception:
        return {n: "n/a" for n in names}
    counts = {n: 0 for n in names}
    for line in text.splitlines():
        n, _, author = line.strip().partition("\t")
        for name in names:
            if name.lower() in author.lower():
                counts[name] += int(n)
    return counts


def render(summary, commits=None):
    total_earned = sum(m["earned"] for m in summary.values())
    total_planned = sum(m["planned"] for m in summary.values())
    head = "| Member | Stories done | Points earned | Points planned | Share of earned points |"
    sep = "|---|---|---|---|---|"
    if commits is not None:
        head += " Commits |"
        sep += "---|"
    lines = [head, sep]
    for name, m in summary.items():
        share = (100.0 * m["earned"] / total_earned) if total_earned else 0.0
        row = "| %s | %d | %d | %d | %.1f%% |" % (name, m["done"], m["earned"], m["planned"], share)
        if commits is not None:
            row += " %s |" % commits.get(name, "n/a")
        lines.append(row)
    lines.append("| **Team** | %d | %d | %d | 100%% |" % (
        sum(m["done"] for m in summary.values()), total_earned, total_planned) + (" |" if commits is not None else ""))
    return "\n".join(lines)


def write_readme(readme, table):
    text = Path(readme).read_text()
    if START not in text or END not in text:
        raise SystemExit("README is missing the %s ... %s markers" % (START, END))
    pre, rest = text.split(START, 1)
    _, post = rest.split(END, 1)
    Path(readme).write_text(pre + START + "\n" + table + "\n" + END + post)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backlog", default="docs/backlog.csv")
    ap.add_argument("--git", action="store_true")
    ap.add_argument("--write-readme")
    a = ap.parse_args()
    summary = summarize(load(a.backlog))
    table = render(summary, commit_counts(list(summary)) if a.git else None)
    if a.write_readme:
        write_readme(a.write_readme, table)
    print(table)


if __name__ == "__main__":
    main()
