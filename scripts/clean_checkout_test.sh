#!/usr/bin/env bash
# Clone the repo into an EMPTY directory and run the one documented command.
# This is the proof the rubric asks for: "Someone outside the team can clone the repository,
# follow the README, and reproduce the reported numbers." Run it on a machine that is not yours.
#
#   scripts/clean_checkout_test.sh [repo-url] [branch]
#
# Assumes the kairos conda environment is active (see README). Set QUICK=1 for the demo path.
set -euo pipefail
URL="${1:-$(git config --get remote.origin.url)}"
BRANCH="${2:-main}"
WORK="$(mktemp -d)"
echo "clean checkout in $WORK"
git clone --depth 1 --branch "$BRANCH" "$URL" "$WORK/repo"
cd "$WORK/repo"
START=$(date +%s)
make reproduce QUICK="${QUICK:-0}"
python -m kairos_repro.eval.check_headline --run results/paper_faithful --seed 0
echo "clean-checkout run finished in $(( $(date +%s) - START )) seconds"
