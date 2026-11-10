# Rubric to evidence map

Source: Capstone Grading Rubric, Capstone Presentation Rubric, Readiness Checklist, kickoff deck (Session 98).
Capstone = 45% of the course grade. Levels award 0, 10, 30, 60, 80 or 100% of a criterion's weight.

## 1. Paper selection and proposal (1%)
| Criterion (weight) | Evidence | Owner |
|---|---|---|
| Paper and claim (40) | Venue and year, last 3 years, high h5; exact claim as a table row (CLAUDE.md, README) | Emiliano |
| Feasibility evidence (30) | `make data` loads the data; method described in the paper (docs/PLAN.md) | Emiliano |
| Team and logistics (20) | docs/team.md, collaborators added, recorded unanimous commit vote | Aaliyah, Jonas |
| Risk and fallback (10) | docs/risks.md | Jonas |

## 2. Reproduction: working pipeline (15%)
| Criterion (weight) | Evidence | Owner |
|---|---|---|
| Pipeline completeness (35) | `make reproduce` from a clean checkout; scripts/clean_checkout_test.sh passes on another machine | Jonas |
| Fidelity to the paper (30) | configs/paper_faithful.json + docs/deviations.md | Jonas |
| Comparison to published results (25) | results/*/comparison_seed*.md, gap quantified | Aaliyah |
| Reproducibility hygiene (10) | seeds, PYTHONHASHSEED, pinned versions recorded in results | Aaliyah |

## 3. GitHub repository (9%)
| Criterion (weight) | Evidence | Owner |
|---|---|---|
| Runs from a clean checkout (35) | README + clean-checkout test by an outsider | Jonas |
| Commits stand behind the board (30) | Every closed card has commits; history spans the semester | All |
| Contribution is visible (25) | Individual commits; contribution table at the bottom of README (missing table caps this at Missing) | All |
| Evidence stored where cited (10) | Figures and logs under results/ at the paths the Wiki cites | Aaliyah |

## 4. Project board (8%)
| Criterion (weight) | Evidence | Owner |
|---|---|---|
| User stories with story points (35) | docs/backlog.csv sized before work starts; points drive individual grades | All |
| Planned across the semester (35) | Milestones and iterations moving week by week; not filled in at the end | All |
| Assigned, current, complete (20) | Assignee, milestone, iteration on every item; status matches reality | All |
| Coordination is visible (10) | Blockers, handoffs, decisions recorded in issues | All |

## 5. Wiki reproduction report (5%)
| Criterion (weight) | Evidence | Owner |
|---|---|---|
| Claim and result (35) | docs/wiki/Claim-and-Result.md | Emiliano |
| Method and deviations (35) | docs/wiki/Method-and-Deviations.md | Jonas |
| Explanation of the gap (20) | docs/wiki/Gap-Explanation.md (a documented negative result earns full marks) | Aaliyah |
| Structure and navigation (10) | _Sidebar.md, clean headings, working links | Aaliyah |

## 6. Final presentation (7%)
Live reproduction 40 (clone into an empty folder, print one number; recording in repo as fallback),
the reproduction told honestly 30 (claim, data, pipeline, baseline, comparison, every unstated choice),
professionalism and Q&A 30 (10-15 minutes, every member presents their user stories).
Missing the slot: automatic 15% off the team's capstone grade.

## Individual grade
Individual = team score x N x contribution %, capped per component. Contribution % = story points earned / team total,
checked against the board and commit history.
