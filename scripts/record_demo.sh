#!/usr/bin/env bash
# Record the clean-checkout run to docs/demo/ as the rubric's required fallback recording.
# This saves a terminal log. Also screen-record the run and save the video next to the log
# (the fallback must play from the presentation machine with no network).
set -euo pipefail
mkdir -p docs/demo
STAMP=$(date +%Y%m%d-%H%M)
script -q -c "scripts/clean_checkout_test.sh" "docs/demo/clean_checkout_${STAMP}.log"
echo "saved docs/demo/clean_checkout_${STAMP}.log"
