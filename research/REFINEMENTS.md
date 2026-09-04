# Research Program Refinements — evidence-backed, reversible

Prime Agent's `/refine` pattern applied to our research program: after each
campaign, the loop may propose ONE edit to `program.md` (backlog, metric,
or protocol). Every refinement is recorded here with its trigger and
outcome, and can be reverted by ID. The human's steering authority is
unchanged: refinements touch backlog/protocol only — never the locked
harness, the seal, or the paper trader.

Format:

    ## R-<n> | <date> | <status: kept | reverted>
    Trigger: <what observation forced this>
    Evidence: <metrics/citations>
    Edit: <exact change to program.md>
    Rollback: <what to restore>

## R-1 | 2026-08-24 | kept
Trigger: Campaign C honest null (EV ≈ −fee) despite supervised models at
52–56% accuracy; REINFORCE stopping-contrast too weak.
Evidence: research/rlenv/OBSERVATIONS.jsonl (campaign C); LOG.md analysis.
Edit: adopt all-actions contextual-bandit trainer (full-information
advantages) replacing truncated-trajectory REINFORCE.
Rollback: git history retains agent.py pre-campaign-C version.

## R-2 | 2026-08-25 | kept
Trigger: Campaign B invalidated by degenerate {0,1} fair values; two units
bugs found in env/fairvalue.
Evidence: tests/test_rlenv.py failures pre-fix; entry-price inspection.
Edit: add VERIFIER_GATE.md checklist as merge requirement for any
environment/reward change.
Rollback: delete VERIFIER_GATE.md, remove gate references from program.md.
