#!/usr/bin/env python3
"""Read-only health check of the whole project: backlog, board, repo text, results and tests.

    python scripts/verify_all.py            # everything (needs gh login for the board part)
    python scripts/verify_all.py --no-gh    # skip the GitHub board part

It changes nothing. Each line is OK, WARN (worth a look) or FAIL (something is wrong).
The exit code is 1 if anything failed.
"""
import argparse
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
counts = Counter()


def report(level, msg):
    counts[level] += 1
    print("  %-4s %s" % (level, msg))


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def body_of(r):
    return ("**Acceptance:** %s\n\n**Story points:** %s\n**Iteration:** %s\n**Owner:** %s\n"
            % (r["acceptance"], r["points"], r["iteration"], r["owner"]))


def check_backlog():
    print("\n1. Backlog file (docs/backlog.csv)")
    rows = list(csv.DictReader(open(ROOT / "docs/backlog.csv", newline="")))
    handles = json.loads((ROOT / "scripts/handles.json").read_text())
    ids = [r["id"] for r in rows]
    dup = [i for i, n in Counter(ids).items() if n > 1]
    report("FAIL" if dup else "OK", "duplicate story ids: %s" % dup if dup else "%d stories, no duplicate ids" % len(rows))
    dupstory = [s for s, n in Counter(r["story"] for r in rows).items() if n > 1]
    if dupstory:
        report("FAIL", "the same story sentence appears twice: %s" % [s[:50] for s in dupstory])
    for ms in sorted({i[:2] for i in ids}):
        nums = sorted(int(i[3:]) for i in ids if i.startswith(ms))
        if nums != list(range(1, len(nums) + 1)):
            report("WARN", "%s numbering has gaps or does not start at 01: %s" % (ms, nums))
        else:
            report("OK", "%s numbered %s-01..%s-%02d with no gaps" % (ms, ms, ms, len(nums)))
    for r in rows:
        if not re.fullmatch(r"M\d-\d\d", r["id"]):
            report("FAIL", "bad id %r" % r["id"])
        if r["owner"] not in handles:
            report("FAIL", "%s owner %r not in scripts/handles.json" % (r["id"], r["owner"]))
        if not r["points"].isdigit():
            report("FAIL", "%s points %r is not a number" % (r["id"], r["points"]))
        if not r["milestone"].startswith(r["id"][:2] + " "):
            report("FAIL", "%s is in milestone %r, which does not match its id" % (r["id"], r["milestone"]))
        if not r["acceptance"].strip():
            report("FAIL", "%s has no acceptance text" % r["id"])
    pts = Counter()
    for r in rows:
        pts[r["owner"]] += int(r["points"])
    total = sum(pts.values())
    report("OK", "points: %s, total %d" % (", ".join("%s %d" % kv for kv in sorted(pts.items())), total))
    if total and max(pts.values()) - min(pts.values()) > 0.15 * total / len(pts):
        report("WARN", "points are uneven between members")
    return rows


def check_board(rows):
    print("\n2. GitHub board (issues, milestones, labels)")
    res = run(["gh", "issue", "list", "--state", "all", "--limit", "500",
               "--json", "number,title,body,labels,milestone,assignees,state"])
    if res.returncode != 0:
        report("FAIL", "gh could not list issues: %s" % res.stderr.strip()[:200])
        return
    issues = json.loads(res.stdout)
    handles = json.loads((ROOT / "scripts/handles.json").read_text())
    by_id = {}
    for i in issues:
        m = re.match(r"\[(M\d-\d\d)\] ", i["title"])
        if m:
            by_id.setdefault(m.group(1), []).append(i)
        else:
            report("WARN", "issue #%d is not a story: %s" % (i["number"], i["title"][:60]))
    want = {r["id"]: r for r in rows}
    for sid, lst in sorted(by_id.items()):
        if len(lst) > 1:
            report("FAIL", "%s has %d issues: %s" % (sid, len(lst), ", ".join("#%d" % i["number"] for i in lst)))
        if sid not in want:
            report("FAIL", "issue #%d %s has no row in the backlog" % (lst[0]["number"], sid))
    bad = 0
    for sid, r in want.items():
        if sid not in by_id:
            report("FAIL", "%s has no issue on GitHub" % sid)
            bad += 1
            continue
        i = by_id[sid][0]
        problems = []
        if i["title"] != "[%s] %s" % (sid, r["story"]):
            problems.append("title differs from the backlog")
        if (i["body"] or "").replace("\r\n", "\n").strip() != body_of(r).strip():
            problems.append("description differs from the backlog")
        labels = sorted(l["name"] for l in i["labels"])
        if labels.count("points:" + r["points"]) != 1 or any(l.startswith("points:") and l != "points:" + r["points"] for l in labels):
            problems.append("points label %s, backlog says points:%s" % ([l for l in labels if l.startswith("points:")], r["points"]))
        ms = (i.get("milestone") or {}).get("title")
        if ms != r["milestone"]:
            problems.append("milestone %r, backlog says %r" % (ms, r["milestone"]))
        who = sorted(a["login"] for a in i["assignees"])
        if who != [handles[r["owner"]]]:
            problems.append("assignee %s, backlog says %s" % (who, handles[r["owner"]]))
        if i["state"] != "OPEN" and r["status"] != "done":
            problems.append("issue is %s but the backlog status is %r" % (i["state"].lower(), r["status"]))
        for p in problems:
            report("FAIL", "#%d %s: %s" % (i["number"], sid, p))
        bad += bool(problems)
    if not bad:
        report("OK", "all %d stories have exactly one issue with matching title, description, points, milestone and assignee" % len(want))
    res = run(["gh", "api", "repos/:owner/:repo/milestones?state=all&per_page=100"])
    if res.returncode == 0:
        have = Counter(m["title"] for m in json.loads(res.stdout))
        need = {r["milestone"] for r in rows}
        for t in sorted(need - set(have)):
            report("FAIL", "milestone %r is missing" % t)
        for t in sorted(set(have) - need):
            report("WARN", "milestone %r is not used by any story (delete it on GitHub if it is a leftover)" % t)
        for t, n in have.items():
            if n > 1:
                report("FAIL", "milestone %r exists %d times" % (t, n))
        if need <= set(have):
            report("OK", "all %d milestones exist" % len(need))
    res = run(["gh", "label", "list", "--limit", "200", "--json", "name"])
    if res.returncode == 0:
        used = {"points:" + r["points"] for r in rows}
        for l in sorted(x["name"] for x in json.loads(res.stdout) if x["name"].startswith("points:")):
            if l not in used:
                report("WARN", "label %s is not used by any story (harmless; delete it if you like)" % l)


def check_text(rows):
    print("\n3. Story ids mentioned in the repo's text files")
    ids = {r["id"] for r in rows}
    found = 0
    for p in sorted(ROOT.rglob("*")):
        rel = p.relative_to(ROOT)
        if not p.is_file() or rel.parts[0] in (".git", "data") or p.suffix not in (".md", ".py", ".csv", ".json", ".sh", ".yml", ".txt", "") \
                or rel.as_posix() in ("docs/backlog.csv", "scripts/verify_all.py", "scripts/sync_board.py"):
            continue
        try:
            text = p.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in re.finditer(r"\bM(\d)-(\d\d)(?:\.\.M\d-(\d\d))?", line):
                ends = [m.group(0)[:5]] + (["M%s-%s" % (m.group(1), m.group(3))] if m.group(3) else [])
                for sid in ends:
                    if sid not in ids:
                        report("FAIL", "%s:%d mentions %s, which is not in the backlog" % (rel, n, sid))
                        found += 1
    if not found:
        report("OK", "every story id mentioned in docs, code and README exists in the backlog")
    sched = (ROOT / "docs/schedule.md").read_text()
    for r in rows:
        it = r["iteration"].split()[-1]
        line = next((l for l in sched.splitlines() if l.startswith("| %s |" % it)), "")
        ranges = re.findall(r"M(\d)-(\d\d)(?:\.\.M\d-(\d\d))?", line)
        whole = re.findall(r"\bM\d\b(?!-)", line) if "all M" in line else []
        ok = r["id"][:2] in whole or any(
            r["id"][1] == a and int(b) <= int(r["id"][3:]) <= int(c or b) for a, b, c in ranges)
        if not ok:
            report("WARN", "%s is in %s in the backlog but not in that row of docs/schedule.md" % (r["id"], r["iteration"]))


def check_results():
    print("\n4. Results committed so far")
    for f in ("results/data_report.md", "results/graph_features.csv", "results/env_report.txt",
              "results/baselines/do_nothing/comparison_seed0.md", "results/baselines/histogram_distance/comparison_seed0.md"):
        p = ROOT / f
        report("OK" if p.exists() and p.stat().st_size else "FAIL", ("%s present" if p.exists() else "%s missing") % f)
        if p.exists() and run(["git", "ls-files", "--error-unmatch", f]).returncode != 0:
            report("WARN", "%s exists but is not committed" % f)
    env = ROOT / "results/env_report.txt"
    if env.exists():
        lines = [l for l in env.read_text().splitlines() if l.strip() and not l.startswith("#")]
        report("OK" if len(lines) >= 3 else "WARN", "%d memcheck line(s) in env_report.txt (need one per member for M1-01)" % len(lines))


def check_git_and_tests():
    print("\n5. Git and tests")
    br = run(["git", "branch", "--show-current"]).stdout.strip()
    dirty = run(["git", "status", "--porcelain"]).stdout.strip()
    report("OK" if br == "main" else "WARN", "on branch %s" % br)
    report("WARN" if dirty else "OK", "uncommitted changes:\n         " + dirty.replace("\n", "\n         ") if dirty else "nothing uncommitted")
    run(["git", "fetch", "-q", "origin"])
    behind = run(["git", "rev-list", "--count", "HEAD..origin/main"]).stdout.strip()
    if behind and behind != "0":
        report("WARN", "%s commit(s) on origin/main that you do not have: run git pull" % behind)
    stray = [b.strip("* ").strip() for b in run(["git", "branch"]).stdout.splitlines() if b.strip("* ").strip() not in ("main", br)]
    if stray:
        report("WARN", "local branches besides main and the current one: %s" % ", ".join(stray))
    res = run([sys.executable, "-m", "pytest", "-q"])
    last = (res.stdout.strip().splitlines() or ["no output"])[-1]
    report("OK" if res.returncode == 0 else "FAIL", "tests: %s" % last)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-gh", action="store_true")
    a = ap.parse_args()
    rows = check_backlog()
    if not a.no_gh:
        check_board(rows)
    check_text(rows)
    check_results()
    check_git_and_tests()
    print("\nSummary: %d OK, %d WARN, %d FAIL" % (counts["OK"], counts["WARN"], counts["FAIL"]))
    sys.exit(1 if counts["FAIL"] else 0)


if __name__ == "__main__":
    main()
