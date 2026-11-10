# Claude Code prompts

## Session start (every session)
> Read CLAUDE.md and docs/deviations.md. Run git status and tell me which branch I am on, what is uncommitted, and whether I am behind main. We are working on story M_-__ from docs/backlog.csv.

## For any story
> Read CLAUDE.md. Implement story <id> as the acceptance criterion in docs/backlog.csv says. Write the code ourselves from the paper (IDS_PROJECT.pdf); do not copy the authors' files. If you need a value the paper does not give, stop, propose it, and add a row to docs/deviations.md before using it. Add or update a test. Tell me exactly what to commit and a message to use. Do not run git add, commit or push.

## Checking a "check" row against the authors' source
> Open the authors' file named in docs/deviations.md (ubc-provenance/kairos, StreamSpot/src). Confirm or correct the value in the row, quote the line number, and update the Status column. Do not copy code.
