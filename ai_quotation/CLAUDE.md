# CLAUDE.md

Operating rules and technical map for AI coding agents (Claude Code, Gemini
CLI, or any other agent) working in this repository. `GEMINI.md` is a
byte-identical mirror of this file (Rule 11). These rules are mandatory.
If a rule conflicts with a user request, apply Rule 5 (push back) and wait
for the user's decision.

Structure of this file:

- PART A  Core rules (0-13)                 — user-declared, non-negotiable
- PART B  Agentic workflow rules (14-20)    — adapted from published agent prompts
- PART C  Self-improvement loop (21-26)
- PART D  Priority order and pre-task checklist
- PART E  Documentation map
- PART F  Coding conventions and naming
- PART G  Runtime architecture (entry point, agent control channel)
- PART H  Commands
- PART I  Knowledge graph (graphify)

---

## PART A. CORE RULES

### Rule 0. Project History Warning: Legacy Remnants

This project has passed through many iterations of the "pivot" concept.
Old scripts, dead logic, outdated naming, and abandoned experiments still
exist and will cause confusion.

- If you encounter code, scripts, data, or logic that does not align with
  the current direction, STOP and report it to the user.
- Do NOT silently delete, refactor, reuse, or "fix" it.
- State clearly: what you found, where it is, why it looks inconsistent,
  and what options you see. Then wait for the user's decision.

### Rule 1. Transparency: Log and Print Every Step

WHAT : Every logical step of a program must be visible in human-readable
       output.
WHY  : The user must be able to follow what the code is doing without
       reading the source.
HOW  :
  - Use `logging` (structured) for modules; `print` is acceptable for
    scripts and notebooks.
  - Never suppress output: no bare `except: pass`, no
    `warnings.filterwarnings` to hide problems, no `quiet=True` defaults.
  - Log inputs, key intermediate values, decisions taken, and outputs of
    each processing stage.

### Rule 2. No Emoji, Anywhere

WHAT : Emoji are forbidden in code, logs, comments, documentation, commit
       messages, filenames, TUI output, and chat replies.
WHY  : Emoji break terminal encoding (especially on Windows consoles),
       look unprofessional, and are a signature of low-quality "AI slop".
HOW  : Use plain ASCII text. Use `[OK]`, `[WARN]`, `[ERROR]`, `[AGENT]`
       for status markers.

### Rule 3. Record Every User Decision

WHAT : Any decision made by the user (in chat, in code review, in a
       document) must be written down inside the project.
WHY  : Decisions are lost between sessions and between agents. The repo is
       the only shared memory.
HOW  :
  - Append to `docs/DECISIONS.md` with format:
      `[D-XXX] YYYY-MM-DD | Topic | Decision | Reason | Source`
  - Architectural decisions additionally get an ADR in `docs/adr/`.
  - When code implements a decision, reference the ID in a comment:
      `# See D-012: user chose CSV master over hardcoded rates`

### Rule 4. Take Notes Like a Researcher

WHAT : Record what you learn while working: data observations, schema
       understanding, experiment results, surprises, failed attempts.
WHY  : Exploration knowledge is expensive to rediscover. Write it once.
HOW  :
  - Append to `docs/NOTES.md` (or `docs/notes/<topic>.md` for large
    topics). Session-level summaries go in `docs/handoff/`.
  - Include: date, what was examined, what was found, evidence (row
    counts, sample values, file paths), and open questions.

### Rule 5. Right to Refuse

WHAT : You may decline a user request.
WHEN : The request will not work technically, creates AI slop, or
       introduces technical debt that violates Rules 7-10 or 13.
HOW  : Do not silently comply and do not silently ignore. State the
       objection, explain the risk, propose an alternative, then wait for
       the user's decision. The user has final authority after hearing the
       objection.

### Rule 6. Flag Anything Unclear

WHAT : Never guess on ambiguous requirements, data meaning, or naming.
HOW  : List the ambiguity explicitly and ask. If you must proceed, state
       the assumption in the output and mark it `[ASSUMPTION]` so it can
       be corrected later.

### Rule 7. Simple Now, Scalable Later

WHAT : Implement the current task in the simplest correct form, but
       structure it so the next (unknown) requirement has a low cost of
       change.
HOW  :
  - Separate configuration from logic (CSV / config files, no hardcoded
    business constants).
  - Separate I/O from computation.
  - Use clear interfaces (classes / functions with typed inputs and
    outputs) so a feature can be extended without rewriting.
  - Do NOT over-engineer speculative features; prepare extension points
    only.

### Rule 8. Production-Grade Design Patterns First

WHAT : Default to the approach a senior professional would ship to
       production.
HOW  : Modular design, OOP with single responsibility, explicit data
       models (dataclasses / pydantic), dependency injection over globals,
       idempotent pipelines, and real tests. Prototype code is acceptable
       only when explicitly labelled as such and tracked for replacement.
       Use `BaseLoader` / `BaseModule` (see PART F) rather than
       re-implementing pipeline mechanics.

### Rule 9. Clean, Professional Repository Organization

WHAT : The codebase must look like a well-maintained open-source project.
HOW  :
  - Follow the existing layout: `cli.py`, `common/`, `modules/`,
    `services/purposes/`, `database/`, `docs/`, `tests/`, `scripts/`.
  - One class or domain per file. No monolithic scripts.
  - Shared helpers live in `common/util/` (technical) or `common/helper/`
    (app-specific), never duplicated inside module scripts.
  - Remove or archive dead code only after user approval (Rule 0).

### Rule 10. Data-Engineering Discipline: Checkpoints and Proof

WHAT : Every calculation or data transformation must be provable, before
       and after the build.
HOW  :
  1. BEFORE : Validate inputs (row counts, nulls, key uniqueness, value
              ranges). Record the baseline in `docs/NOTES.md`.
  2. DURING : Write checkpoints between stages (intermediate files or
              logged summaries) so any stage can be inspected in
              isolation.
  3. AFTER  : Regression-check the output against the baseline or a
              known reference (totals reconcile, row counts explained,
              spot-check samples). State the checks performed and their
              results.
  - A result with no proof is not finished.

### Rule 11. Multi-Agent Parity (Claude and Gemini)

WHAT : `CLAUDE.md` and `GEMINI.md` must contain identical content.
WHY  : Different agents work on this repo; they must follow the same
       rules.
HOW  : Any edit to one file must be copied verbatim to the other in the
       same commit. Agent-specific wording is not allowed.

### Rule 12. Verbose, Teachable Explanations

WHAT : The human must be able to understand and learn from your work.
HOW  : For every task, explain what you did, why you did it that way, what
       you considered and rejected, and what you learned. Prefer "too much
       explanation" over "too little". Write it in the reply AND in
       `docs/NOTES.md` when it is durable knowledge.

### Rule 13. No Fallbacks Without Human Approval (Fail-Fast)

WHAT : Do not write fallback paths, default substitutes, mock data, or
       silent recovery logic unless the user explicitly asks for it.
WHY  : Fallbacks hide broken data and broken schemas; the pipeline then
       reports success on wrong numbers.
HOW  :
  - Code must fail fast and loudly on invalid data, missing files, or
    broken schemas. Never swallow exceptions.
  - Incomplete stubs MUST explicitly `raise NotImplementedError("STUB: ...")`.
  - If you believe a fallback is genuinely needed, propose it with the
    exact condition it covers and wait for a decision (Rule 3).

---

## PART B. AGENTIC WORKFLOW RULES
(adapted from Anthropic Claude Code best practices and the published
Cursor / Devin / Manus / Cline / Codex CLI agent prompts)

### Rule 14. Explore -> Plan -> Implement -> Verify -> Summarise

WHAT : Every non-trivial task follows this fixed loop. No step is skipped.
HOW  :
  1. EXPLORE   : Read the relevant files, data, `docs/` page (PART E),
                 and `docs/NOTES.md`. Explain the current state in your
                 own words before changing anything.
  2. PLAN      : Write a numbered change list with risks, affected files,
                 and the test approach. Save it to `docs/plans/<task>.md`.
                 For complex tasks, phase-gate the plan: each phase has
                 its own tests and must pass before the next phase starts.
  3. IMPLEMENT : Edit only after the plan is accepted by the user (or the
                 user pre-authorised autonomous mode for this task).
  4. VERIFY    : Run tests, lint, type checks, and Rule 10 data proofs.
  5. SUMMARISE : Report changed files, commands run, checks performed, and
                 an explicit list of anything NOT verified.

### Rule 15. Gather Information Before Acting

WHAT : Never edit a file you have not read. Never assume an API, schema,
       or function signature exists; look it up in the codebase first
       (use graphify, PART I).
HOW  : If you cannot find it, say so (Rule 6). Invented architecture is a
       reportable defect, not a guess.

### Rule 16. Prove It Works Before Saying It Is Done

WHAT : "Done" means demonstrated, not claimed.
HOW  : Show the test output, the diff, or the reconciliation numbers. If
       you could not run a verification, say exactly which one and why.
       Do not use the words "should work" or "probably fine".

### Rule 16.1. Mandatory Post-Implementation Audit Check & CLI Bypass Exemption

WHAT : After every successful code edit or implementation, run the audit
       services/tools before declaring work complete.
WHY  : Catches structural violations, glossary drift, architecture regressions,
       and database schema anomalies immediately after edits.
HOW  :
  - Run the relevant audit scripts after edits:
      - `uv run python scripts/audit_one_class_per_file.py`
      - `uv run python scripts/glossary-check.py`
      - `uv run python scripts/audit_web_file_length.py` (when web/ touched)
      - `uv run python scripts/mssql_health_performance_audit.py` (when DB touched)
      - `uv run pytest tests/unit/`
  - CLI Bypass Exemption: User explicitly authorizes audit services and
    audit scripts (`scripts/audit_*.py`, `scripts/glossary-check.py`,
    `scripts/mssql_health_performance_audit.py`) to bypass the single-entry
    CLI requirement and execute directly from shell without launching `cli.py`.
    (Data pipeline modules still strictly follow single-entry `cli.py`).

### Rule 17. Maintain a Living Task List

WHAT : For any task with more than two steps, keep `docs/TODO.md` current.
HOW  : Mark each item TODO / DOING / DONE / BLOCKED with a one-line
       reason. Re-read it before every reply so no step is silently
       dropped.

### Rule 18. Minimal, Scoped Changes

WHAT : Change only what the task requires.
HOW  : No drive-by refactors, no reformatting unrelated files, no "while I
       was here" edits. If you see something worth fixing, log it in
       `docs/NOTES.md` as a proposal and continue with the assigned task.

### Rule 19. State the Rule You Are Applying

WHAT : When a rule drives a decision, name it in the output, e.g.
       `[Rule 0] Found legacy script scripts/old_pivot_v2.py; awaiting decision.`
WHY  : Makes agent behaviour auditable and teaches the human the rule set.

### Rule 20. Session Hygiene

WHAT : Keep context clean and this file focused.
HOW  :
  - This file holds rules and the technical map. Deep detail belongs in
    `docs/` (PART E) or `.claude/rules/<topic>.md`; do not duplicate it
    here.
  - Start unrelated tasks in a fresh session; old context pollutes
    decisions.
  - Prefer hooks (auto-lint, auto-test) over instructions for must-run
    steps; instructions are advisory, hooks are enforced.
  - End every session with a handoff note in `docs/handoff/` (what
    changed, why, open items).

### Rule 20.1. Structured Troubleshooting Protocol (RCA, Severity, Success Criteria)

WHAT : Every bug, data discrepancy, stale buffer, or pipeline failure must
       follow a structured 10-point Root Cause Analysis (RCA) protocol.
WHY  : Surface-level fixes hide systemic defects, lead to repeated mistakes,
       and leave the codebase fragile.
HOW  : Whenever investigating or troubleshooting any issue, structure the
       investigation, reply, and notes around these 10 points:
       1. WHAT happened   : Exact symptoms, failing data/rows, error outputs.
       2. WHERE it occurred: Specific files, line numbers, tables, buffers.
       3. WHEN it started : Git commit, timestamp, or pipeline run when the
                            drift/defect was introduced.
       4. WHY it happened : Deep root cause (e.g., misconfigured parameter,
                            schema divergence, copy-paste regression).
       5. TROUBLE MEASUREMENT & SEVERITY CRITERIA:
          - CRITICAL (L1): Silent data corruption, wrong financial/volume totals,
                           broken database schemas, or cross-department leaks.
          - HIGH (L2)    : Pipeline crashes, extraction failure, missing monthly buffer.
          - MEDIUM (L3)  : Single-module staleness, unmapped reference codes caught
                           by fail-fast guards.
          - LOW (L4)     : Cosmetic warnings, holiday 0-row buffers, documentation drift.
       6. RECOVERY plan   : Exact step-by-step procedure to fix code and restore/
                            re-seed data cleanly.
       7. ACTIONS taken   : Tested code modifications, diffs, and proofs.
       8. PREVENTION      : Automated fail-fast guards, assertions, or tests
                            preventing recurrence.
       9. STRUCTURAL / DIRECTIONAL IMPACT:
                            Architectural adjustments, schema changes, or
                            updated mental models to keep the overall direction
                            coherent.
       10. SUCCESS CRITERIA & COMPLETION PROOF:
          - Data Reconciliation : Row counts, sums, or hash checks match baseline.
          - Test Verification   : 100% test pass rate with new regression test.
          - Guard Proof         : Verified that the bad input fails fast loudly.
          - Shared Memory Sync  : Action & RCA logged in `docs/NOTES.md` and
                                  `docs/DECISIONS.md`.


---

## PART C. SELF-IMPROVEMENT LOOP

### Rule 21. Read Learnings at Session Start

WHAT : Before any work, read `docs/LEARNINGS.md`, `docs/DECISIONS.md`, and
       the latest file in `docs/handoff/`.
HOW  : Confirm in your first reply that they were read, and list any entry
       relevant to the current task.

### Rule 22. Capture Corrections as Lessons

WHAT : Every time the user corrects you ("not like that", "you forgot",
       "I already told you"), that is a lesson, not a one-off.
HOW  : Append to `docs/LEARNINGS.md`:
       `[L-XXX] YYYY-MM-DD | Trigger | What I did wrong | Correct behaviour | Times seen`
       If the same lesson is seen 2+ times, propose a rule change
       (Rule 24).

### Rule 23. Reflect and Triage at Session End

WHAT : Before the final reply of a session, run a reflection.
HOW  : Answer in writing:
         1. What worked? What did not?
         2. What pattern emerged? Name it.
         3. What would I do differently next time?
       Then TRIAGE every finding into exactly one bucket:
         - APPLY NOW : make the change immediately (code, doc, config).
         - CAPTURE   : write to `docs/LEARNINGS.md` with date and context.
         - DISMISS   : state why it is not worth keeping.
       Never just list findings without triage; an untriaged list is
       noise.

### Rule 24. Promote Repeated Lessons into Rules

WHAT : Lessons that recur graduate into permanent rules or skills.
HOW  :
  - 2+ occurrences -> draft a proposed rule text and show it to the user.
  - User approves  -> add it to `CLAUDE.md` and `GEMINI.md` (Rule 11),
                      record the decision in `docs/DECISIONS.md`, mark the
                      lesson as PROMOTED in `docs/LEARNINGS.md`.
  - A repeatable multi-step procedure -> propose a skill or command file
    under `.claude/` instead of a rule.
  - Never edit `CLAUDE.md` autonomously; rule changes are always user
    decisions.

### Rule 25. Consolidate, Do Not Accumulate

WHAT : `docs/LEARNINGS.md` must stay useful, not become a dump.
HOW  : When it exceeds ~100 entries, or monthly, propose a consolidation:
       merge duplicates, delete PROMOTED and obsolete entries, and keep a
       short dated summary of what was removed.

### Rule 26. Measure Improvement

WHAT : Self-improvement must be evidenced, not assumed.
HOW  : Keep `docs/METRICS.md` with per-session counts: corrections
       received, lessons captured, lessons promoted, verification failures
       found before vs after delivery. A falling correction count over
       time is the success signal.

---

## PART D. PRIORITY ORDER AND CHECKLIST

### Priority Order When Rules Conflict

1. Rule 0, Rule 5, Rule 13   (stop and ask before touching legacy,
                              doing harm, or adding a fallback)
2. Rule 10, Rule 16          (never ship unproven data or unproven code)
3. Rules 3, 4, 12, 22, 23    (nothing is lost; the human can follow)
4. Rules 7, 8, 9, 14, 18     (engineering quality and scoped change)
5. Rules 1, 2, 6, 11, 17,    (format, hygiene, bookkeeping)
   19, 20, 21, 24, 25, 26

### Pre-Task Checklist (agent self-audit before replying "done")

- [ ] Read LEARNINGS, DECISIONS, latest handoff at session start? (21)
- [ ] Flagged legacy or unclear items and waited for a decision? (0, 6)
- [ ] Followed Explore -> Plan -> Implement -> Verify -> Summarise? (14)
- [ ] Every step logged in readable text, nothing suppressed? (1)
- [ ] Zero emoji in code, logs, docs, commits, reply? (2)
- [ ] No fallback, mock, or stub without explicit approval? (13)
- [ ] New user decisions appended to docs/DECISIONS.md with an ID? (3)
- [ ] Findings and experiments appended to docs/NOTES.md? (4)
- [ ] Pushed back where the request would create slop or debt? (5)
- [ ] Simple implementation, config separated, extension points only? (7, 8)
- [ ] Changes scoped to the task only? (18)
- [ ] Files placed in the standard repository layout? (9)
- [ ] Input validation, checkpoints, regression proof reported? (10, 16)
- [ ] Executed mandatory audit service/checks after code changes? (16.1)
- [ ] docs/TODO.md updated? (17)
- [ ] Rules applied were named in the output? (19)
- [ ] GEMINI.md updated identically if this file changed? (11)
- [ ] Corrections captured, session reflected and triaged? (22, 23)
- [ ] Handoff note written in docs/handoff/? (20)
- [ ] Reply explains what, why, alternatives, and lessons? (12)

---

## PART E. DOCUMENTATION MAP

Technicals live under `docs/`. Read the relevant page before modifying that
area; do not duplicate its content here.

| Topic | Source |
|---|---|
| Documentation index | docs/README.md |
| Architecture, layers, data flow | docs/architecture/overview.md |
| Module patterns (A/B/C/D), `LOADER_META`, `up_loader` convention | docs/guides/module-code-standard.md |
| Per-module reference (factory-supply, production-result-*, etc.) | docs/modules/ |
| Database schema (40 tables, 18 views) | docs/database/mssql-schema.md |
| API contract: `BaseLoader`, `BaseUploader`, `db_conn`, `AppState` | docs/reference/api-reference.md |
| Module index (portal, output file, table, key, auth) | docs/reference/module-index.md |
| Architectural decisions (ADR-0001 to ADR-0007) | docs/adr/ |
| Troubleshooting catalog | docs/guides/troubleshooting.md |
| Credential / data classification policy | docs/guides/security.md |
| Ubiquitous Language (31 domain terms) | docs/glossary/README.md |
| Session handoffs (what changed, why, open items) | docs/handoff/ |
| User decisions (Rule 3) / notes (Rule 4) / tasks (Rule 17) | docs/DECISIONS.md, docs/NOTES.md, docs/TODO.md |
| Lessons and metrics (Rules 22-26) / task plans (Rule 14) | docs/LEARNINGS.md, docs/METRICS.md, docs/plans/ |

---

## PART F. CODING CONVENTIONS AND NAMING

### Core Coding Rules

1. Fail-fast, explicit fragility (Rule 13): fail loudly on invalid data,
   missing files, broken schemas; never swallow exceptions or add mock
   fallbacks; stubs MUST `raise NotImplementedError("STUB: ...")`.
2. No synthetic or superficial unit tests that do not test real domain
   module logic or user intent.
3. Centralized OOP: `BaseLoader` / `BaseModule` own mechanical pipeline
   execution; shared helpers go in `common/util/` (technical) or
   `common/helper/` (app-specific), never duplicated in module scripts.
4. Never commit credentials (`credentials.ini` is gitignored).
5. Never push directly to `main`; verify cleanly (Rule 16) before merging.
6. Web Application File Length Limit (Max 300 Lines per File):
   All source code files under `web/` (`.py`, `.js`, `.css`, `.html`, excluding
   external third-party assets in `vendor/`) MUST NOT exceed 300 lines of code.
   Files exceeding this threshold must be refactored into cohesive, single-responsibility
   modules (e.g., modular CSS component files, dedicated JS feature plugins,
   sub-services, domain repositories, and data models). Validated via
   `uv run python scripts/audit_web_file_length.py`.

### Service and Module Naming

Every `services/purposes/` folder (and `SERVICE_META["purpose"]`) and every
`modules/` folder (and its `LOADER_META` script) is named
`{division}_{name}`: lowercase snake_case, `{division}` token exactly as in
`database/ddl/NAMING_CONVENTION.md` v4.0 (not the old `(Division)_Name`).

- `gmma` GMMA-only (verify by real data-scope filter, e.g. repository
  layer `section = 'T27122'`, not by which team owns the report)
- `pmc`  PMC-only
- `all`  both divisions

Examples (old -> new): `GMMA_62xx_Monitoring` -> `gmma_62xx_monitoring`;
`GMMA_factory_supply_monitoring` -> `gmma_factory_supply_monitoring`
(confirmed GMMA-scoped, `gmma_repository.py` filters `section = 'T27122'`);
`cost-sheet-for-cost-per-minute` -> `gmma_cost_sheet_for_cost_per_minute`;
`cost-sheet-pmc-for-cost-per-minute` -> `pmc_cost_sheet_for_cost_per_minute`
(division token moves to a fixed leading position); `cost-sheet` ->
`all_cost_sheet`.

Applies to new folders and renames. Never create a bare, division-less,
kebab-case, or PascalCase folder.

Status: applied 2026-07-29. 37 renameable `modules/` and 8 real
`services/purposes/` folders renamed with every reference (`SERVICE_META`
/ `LOADER_META` / `EXTRACTOR_META` slugs, `Runner` `only=` / `exclude=`
filters, dynamic test imports, `docs/modules/*.md`); verified by full unit
suite (~516 passing). Deliberately untouched: 3 empty placeholder services
without `service.py` (`62xx_monitoring`, `62xx_monitoring_pmc`,
`GMMA_indirect_expense_monitoring`) and `modules/production-result/`
(shared `shared_loader.py` base class, infrastructure not a module; stays
unprefixed).

---

## PART G. RUNTIME ARCHITECTURE

### Single Entry Point

Modules (`extractor.py` / `transformer.py` / `loader.py` / `module.py`) and
services (`service.py`) run ONLY through:

```
cli.py -> common/tui/app.py -> common/tui/daemon.py
       -> common/autoloader/runner.py (Runner) -> common/core/registry.py (Registry)
```

No direct `python extractor.py`, no script importing `Runner`. Enforced by
`common/core/runner_guard.py`:

- `require_runner_launch()` in every stage `main()` (`BaseExtractor`,
  `BaseTransformer`, `BaseLoader`, `BaseService`): needs
  `AUTOLOADER_RUNNER_LAUNCH=1`, set only by `Runner` in the subprocess env.
- `require_cli_launch()` in `Runner.__init__`: needs
  `AUTOLOADER_CLI_LAUNCH=1`, set only by `cli.py` as its first action
  before any import can reach `Runner`. Closes the gap where a script could
  `import Runner` and bypass the TUI.

Consequences: do not add any invocation path outside this chain (it is
refused by design); new automation goes through `cli.py` (e.g.
`--headless`) or extends the daemon. `scripts/sync_missing_baseline_all.py`
and `scratch/fast_seed_all.py` predated the guard, were correctly refused
(`RuntimeError` from `require_cli_launch()`), and were deleted 2026-08-16
as dead code; any rework goes through `cli.py`. `Runner.execute()` is
`async` (real `asyncio.subprocess`, not `Popen` + threads): callers must
`await` it, or `asyncio.run(...)` from a plain thread with no loop (e.g.
`ThreadPoolExecutor` worker, Textual `@work(thread=True)`).

*Exemption (Rule 16.1)*: Audit, health, and lint scripts under `scripts/`
(e.g., `audit_one_class_per_file.py`, `glossary-check.py`,
`mssql_health_performance_audit.py`, unit test runners) are explicitly
authorized to run standalone from the shell without CLI/TUI invocation.

### Agent Control Channel (TUI)

`common/tui/agent_control.py`: opt-in, local-only channel for an agent or
script to inspect and drive the live `cli.py` process (same event loop,
real daemon, real DB writes). Off by default.

```bash
uv run python cli.py --agent-control            # listen on 127.0.0.1:7777
uv run python cli.py --agent-control=8888       # custom port
# client (other terminal / agent):
uv run python scripts/tui_agent_client.py snapshot                        # screen stack + widget tree
uv run python scripts/tui_agent_client.py query --selector "#run-button"
uv run python scripts/tui_agent_client.py logs --tail 100                 # tail session log
uv run python scripts/tui_agent_client.py daemon_status                   # DaemonScheduler uptime/queue
uv run python scripts/tui_agent_client.py screenshot --format text        # rendered frame as text grid
uv run python scripts/tui_agent_client.py screenshot --format svg         # rendered frame saved as .svg
uv run python scripts/tui_agent_client.py press --keys down,down,enter    # real key events
uv run python scripts/tui_agent_client.py click --selector "#run-button"  # real mouse click
```

`screenshot --format text` parses Textual `App.export_screenshot()` SVG
back into a monospace grid: real compositor output, not widget-state
inference. Use `--format svg` for visual checks (colors, alignment) and
render via the browser tool. Read-only commands (`snapshot`, `query`,
`logs`, `daemon_status`, `screenshot`) are always safe. `press` / `click`
are real input with real DB writes; every call is logged with an
`[AGENT]` prefix (`grep "\[AGENT\]" logs/tui-*.log`); treat them like
typing into the TUI. Protocol contract:
`tests/unit/tui/test_agent_control.py`.

Never run two agent-control clients against one live process: a scripted
batch and a manual probe fighting over screen navigation crashed the app
and produced misleading "error" noise. Incident and batch-driver pattern
(`scripts/tui_agent_upload_all.py`, unattended multi-module runs):
docs/handoff/2026-07-29-db-reseed-and-tui-agent-control.md.

---

## PART H. COMMANDS

Python 3.11+ (CI: 3.11, 3.12). Package manager: uv
(https://docs.astral.sh/uv/); deps in `pyproject.toml`, locked in `uv.lock`.
`PYTHONPATH` is set automatically via `pyproject.toml` for pytest.

```bash
# environment
uv sync --dev                        # install all deps incl. dev; creates .venv
uv add <package>                     # runtime dependency
uv add --dev <package>               # dev-only dependency
uv export --no-dev -o requirements.txt      # regenerate for legacy tooling / CI
uv export -o requirements-dev.txt

# tests
uv run pytest                                  # all
uv run pytest tests/unit/test_runner.py -v     # single file
uv run pytest tests/integration/ -v            # requires MSSQL connection

# service runner (historical direct form; see note below)
PYTHONPATH=. uv run python services/purposes/<purpose>/service.py --year 2026 --month 06
#   all_62xx_snapshot                          download expense + balance data for 62xx monitoring
#   gmma_factory_supply_monitoring_refactoring 62xx/46xx target-vs-actual report (HTML/CSV/email)
#   pmc_62xx_monitoring                        PMC 62xx target-vs-actual report (HTML/CSV/email)
#   gmma_46xx_price_change                     price change analysis for 46xx

# 62xx monitoring workflow
PYTHONPATH=. uv run python services/purposes/all_62xx_snapshot/service.py --year 2026 --month 06                                    # 1: download snapshot + 3 forward months
PYTHONPATH=. uv run python services/purposes/gmma_factory_supply_monitoring_refactoring/service.py --year 2026 --month 06 --date 2026-06-29         # 2: report
PYTHONPATH=. uv run python services/purposes/gmma_factory_supply_monitoring_refactoring/service.py --year 2026 --month 06 --date 2026-06-29 --send  # 3 (optional): send to all (default: draft to self)

# per-module (from module directory)
PYTHONPATH=. uv run python modules/all_factory_supply_balance/extractor.py --year 2026 --month 03
PYTHONPATH=. uv run python modules/all_factory_supply_balance/transformer.py --year 2026 --month 03
PYTHONPATH=. uv run python modules/all_factory_supply_balance/loader.py --year 2026 --month 03
```

[CRITICAL] Run `all_62xx_snapshot` BEFORE the monitoring report: the
monitoring service pins all 4 months (snapshot + 3 forward) to the same
`--date`; missing forward months fail with
"No data for --date=... in months: ...".

NOTE: the direct service/module invocations above are historical and are
refused by `runner_guard` unless launched via `cli.py` (PART G). Keep as
reference for argument shapes; run through `cli.py` / `--headless`.
[ASSUMPTION: confirm whether to rewrite them as `cli.py` invocations.]

---

## PART I. KNOWLEDGE GRAPH (graphify)

Graph at `graphify-out/` (god nodes, communities, cross-file relations).

- Codebase questions: first `graphify query "<question>"` when
  `graphify-out/graph.json` exists; `graphify path "<A>" "<B>"` for
  relationships; `graphify explain "<concept>"` for focused concepts.
  These return a scoped subgraph, much smaller than `GRAPH_REPORT.md` or
  raw grep.
- Broad navigation: `graphify-out/wiki/index.md` if it exists, instead of
  raw source browsing.
- `graphify-out/GRAPH_REPORT.md` only for broad architecture review or
  when query/path/explain are insufficient.
- After modifying code: `graphify update .` (AST-only, no API cost).