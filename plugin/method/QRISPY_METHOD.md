# QRISPY Ticket Method

QRISPY is the ticket workflow used in a repository for research and
implementation tasks. It keeps the current state, decisions, implementation plan,
results, and closeout evidence in one ticket directory.

Ticket directories live under:

```text
<ticket root>/<NNN-ticket-slug>/
```

Each repository names its ticket systems and their folders (ticket roots) in `qrispy.json` at the repository root. Rules that hold only in one repository (its domain, machines, tools and projects) live in `<ticket root>/METHOD_LOCAL.md` of its primary ticket root; that file may narrow the rules here but not loosen them. The tickets that the rules here came from are listed in `method/HISTORY.md`.

## v2 changes

This document is the single definition of QRISPY files and fields; `CLAUDE.md` only points here, and the `qrispy:ticket` skill carries the templates. v2 adds, without changing any earlier rule:

- a **File Registry** (below) that every new file type must be entered in before use;
- a **risk card** at the top of every slice note and closeout, and a **"Deviation from design"** field in every slice note (see Slice Notes);
- **Drift** rules for requirement changes and discoveries during a ticket (see Drift);
- three `state.json` fields: `awaiting_user`, `drift`, `lesson_refs` (see State File);
- the repo-wide mistake ledger `<ticket root>/LESSONS.md` (see Lessons);
- per-ticket `CITE.md` citation boundaries and `lavish/` decision pages (see File Registry);
- short rules for git worktrees and regression tests (see Worktrees, Regression Tests);

## File Registry

Every file type a ticket may contain is defined here and nowhere else. The `qrispy:ticket` skill (`skills/ticket/templates/` in the plugin) holds a template for each templated type.

| File | Stage | Required | Holds |
|---|---|---|---|
| `ticket.md` | open | yes | problem, motivation, scope, acceptance criteria (AC IDs), final deliverable pointer |
| `q_questions.md` | Q | yes | questions, recommendations, and the user's answers recorded verbatim; items added later are marked `Q-N (added during <stage>, date)` |
| `r_research.md` | R | when useful | research and codebase/context investigation |
| `i_design.md` | I | yes | design; with `ticket.md` and the Q answers it is the ticket's **intent contract** |
| `s_structure.md` | S | when useful | file/module layout |
| `p_plan.md` | P | yes | slice plan with the user-approval points |
| `y_slice_N.md` | Y | one per slice (`y_slice_2_4.md` for a range) | risk card, what changed, commands, artifacts, findings, deviation from design, next action |
| `z_closeout.md` | Z | before close | risk card, final status, deliverable, findings, limitations, handoff |
| `state.json` | all | yes | machine-readable status (see State File) |
| `revN.md` / `revN_response.md` | review | per round | read-only review audit / finding-by-finding correction map |
| `<stage>_revisit.md` | revisit | per revisit | superseding design when a ticket is reopened |
| `RECIPES.md` | Y | sim/experiment tickets | copy-pasteable reproduction runbook (see Required Files); a repository may prescribe its opening block in `<ticket root>/METHOD_LOCAL.md` |
| `CITE.md` | Z or later | tickets whose numbers are quoted elsewhere | citation boundary: quotable sentences and numbers with source paths, never-quote items with reasons, scope conditions |
| `jobs/<id>/` | Y | any job that outlives a turn | `job.json` (command, start, next step, and with `--gpu`/`--go` the GPU use and the scoped go it relies on), `DONE.json` (exit code, signal, end), `HANDLED.json` (what was done with the result), `job.log` (untracked), and for a worker that cannot message `jobs/worker/status.log` (status lines); written by `qrispy job run`, watched by `qrispy job wait`, listed by `qrispy inbox` |
| `evidence/` | any | optional | scripts, raw model-session streams and tool versions that back a claim in the ticket's notes but are too bulky or too tool-shaped to quote (for example the checker that produced "50/50 OK", the hook versions before and after a fix); a note that relies on it names the path. Keeps evidence out of volatile temp folders |
| `lavish/*.html` | any | optional | decision / result pages opened with Lavish, an optional tool (see the `qrispy:plan-page` skill); the decisions themselves are recorded back into the Markdown files, which stay the record |

Repo-wide files (not inside any ticket):

| File | Role |
|---|---|
| `method/QRISPY_METHOD.md` | this document: the definition of every ticket file and field |
| `<ticket root>/LESSONS.md` | ledger of agent mistakes, one entry per incident (see Lessons) |
| `method/DEV_REVIEW_RECIPE.md` | catalogue of recurring development and review failure classes, explained; `LESSONS.md` entries link into it |
| `method/REVIEW_PROMPT.md` | the fixed instructions a reviewer session receives; the worker passes only the ticket and round number, so it cannot steer the review |
| `qrispy` (the kit's command, `bin/qrispy` in the plugin; `install.py` links it into `~/.local/bin`) | the status view of all tickets, read only (`ls`, `show`, `inbox`, `cite`, `lint`, `questions`); the kit's other tools are its subcommands, some of which write: `job` (long-running work), `review` (review rounds), `worker`, `lock` (the machine's GPU lock), `check-response`, `config`, `init` (set up a repository: writes `qrispy.json`, `<ticket root>/LESSONS.md`, `<ticket root>/METHOD_LOCAL.md`, a `CLAUDE.md` skeleton and `AGENTS.md`, merges `.claude/settings.json`; never overwrites), `rules` (prints `rules/CORE.md`, for agents without the session-start hook), `dashboard --html` (writes one page) |
| `AGENTS.md` (repository root) | a symlink to `CLAUDE.md`, so Codex and other agents read the same instructions; `qrispy init` creates it, `qrispy lint --repo` FAILs when it is missing or not that symlink, and review rounds attest its hash |
| `rules/CORE.md` (in the plugin) | the core rules every session of a repository that uses the kit receives at start (the plugin's SessionStart hook); `qrispy rules` prints them |
| `install.py` (kit root) | per computer: registers the clone as a local marketplace, installs the plugin but leaves it off for the user (a repository's `.claude/settings.json` turns it on), registers the guard hook (`plugin/hooks/guard_git.py`) and the deny rules for every repository, links `~/.local/bin/qrispy`; without `--install` it only checks |
| `qrispy.json` (repository root) | the repository's ticket systems: `systems` (name and ticket folder of each; the first is the primary system, whose tickets a review round names by slug and whose folder holds the shared method documents), `external_systems` (other repositories' ticket systems, not indexed), `known_duplicate_numbers`, `review_scratch`. The only place system names and folders are defined; another repository adopting this workflow writes its own |
| `<ticket root>/METHOD_LOCAL.md` | the repository's own rules on top of this method (its domain, machines, tools and projects), with its sections in the order of the sections here; it may narrow these rules but not loosen them |
| `method/HISTORY.md` | where the rules of the kit's method files came from: one row per ticket reference removed from their text |
| `qrispy config` (`lib/qrispy_config.py` in the plugin) | reads and checks `qrispy.json` for `qrispy`, `qrispy worker`, `qrispy lock`, `qrispy review` and the reviewer agent (subcommands: `ticket-dir`, `primary-root`, `review-scratch`, `external-roots`); a missing or malformed file stops the tool with the reason. Also holds the process helpers `pid_alive` and `parent_pid` (no /proc, which macOS lacks) used by `qrispy`, `qrispy worker` and `qrispy lock`. Tests: the kit's `tests/test_qrispy_config.py`; job tools on any POSIX machine: `tests/test_jobs_portable.py` (where it has run, with the saved outputs, is in the kit README) |
| `<project>/ROADMAP.md` | a project's direction, expected outputs and ledger of claims, experiments, gaps, decisions and risks; one per project, next to that project's ticket root (see Project Roadmap) |

## Required Files

The File Registry above is the definition of each file. Rules it does not carry:

- Short or QRISPY-lite tickets may omit `r_research.md` and `s_structure.md` when they add no value. `z_closeout.md` is required before a ticket is marked closed. A ticket closed by a triage decision gets a short `z_closeout.md` (close kind, date, the user's note verbatim, successor or reason, whether anything is quotable) and a `state.json.triage` record `{date, decision: closed-completed | closed-superseded | parked | keep, note, successor, revisit_when}`; `qrispy` reads that record.
- `RECIPES.md` records procedure-as-run: environment, build, launch, sweep and analysis commands as actually run. It is what makes review recomputation and revisit re-runs executable. When an output is later withdrawn, add a banner pointing to the replacement rather than rewriting the recipe.
- Review, revision and revisit files follow Within-Ticket Review & Revision and Ticket Revisit below.

## Stage Meaning

- `Q`: questions that need confirmation and the user answers.
- `R`: research/context gathered.
- `I`: design drafted.
- `S`: structure selected.
- `P`: plan approved or accepted.
- `Y`: implementation/evaluation slices completed.
- `Z`: closeout completed.

`state.json.current_stage` should move to `closed` only after `z_closeout.md`
exists and names the final deliverable or handoff.

## Slice Notes

Use `y_slice_N.md` for each completed slice. A slice note should include:

- what changed;
- exact commands run;
- result artifacts and stable paths;
- headline metrics or findings;
- caveats and next action.

If several slices are completed together, a combined note such as
`y_slice_2_4.md` is acceptable as long as the covered slice range is clear.

Since v2 every slice note (and `z_closeout.md`) opens with a five-line **risk card**, so the user can read the card and the evidence and skip the body when the risk is low:

```text
> **Risk card**
> - Changed: what this slice changed.
> - Depends on it: which claim, AC or downstream ticket relies on it.
> - Evidence: where the proof is (paths).
> - Risk: low | medium | high, with one reason.
> - Look at: what the user should check, or "nothing".
```

Every slice note also carries a **"Deviation from design"** section: either "none", or a table row per deviation with its kind (requirement / discovery, see Drift), what changed, why, the affected AC, and who approved it.

## Drift

A ticket's intent is its `ticket.md` ACs, its Q answers and its `i_design.md` (or `*_revisit.md`) — not the conversation that produced them. When execution departs from that intent, the departure is recorded; a departure that is recorded is not a mistake, and one that is not recorded is (class `unrecorded-drift` in `<ticket root>/LESSONS.md`).

- **Requirement change** — started by the user ("add this arm", "change AC-3").
- **Discovery** — started by the agent: the design does not work as written and the method must change. The agent proposes, the user approves; when no AC is affected a post-hoc report is enough. A discovery that only makes an AC stricter without changing its meaning is also reported after the fact; one that changes what is delivered or demonstrated needs approval first.

Both kinds are recorded the same way:

1. Add a Q item: `Q-N (added during <stage>, date)` with the user's words and the decision.
2. Fill the slice note's "Deviation from design" row, and append an entry to `state.json.drift`.
3. Never delete the superseded AC or design sentence; keep it and add `(changed by Q-N on <date>: …)` directly below it.
4. If the final deliverable or the scope itself changes, open a new ticket or a revisit (see Ticket Revisit).

## Lessons

`<ticket root>/LESSONS.md` is the repo-wide ledger of agent mistakes. A mistake is an agent action that contradicted a written rule, the user's explicit intent, or the actual state of the repo, and cost user time or evidence. Classes: **`rule-violation`** (a written rule was broken), **`missing-knowledge`** (the needed rule or fact was not written anywhere), **`unrecorded-drift`** (a departure from intent that was not recorded), **`record-mismatch`** (a record that does not match reality: false green, stale status, mis-copied number). Negative results, refuted hypotheses, and recorded requirement changes are not mistakes.

The agent records an entry, unasked, in the same turn when the user corrects it, when a review finds a defect of its making, or when a guard hook blocks it. Promotion: a lesson first goes to the layer that is loaded when that work happens (a skill or a recipe); a written rule broken twice becomes a mechanism (hook, check script, template field); once a mechanism enforces it, the prose is shortened. Adding another warning sentence is not a promotion. Build the mechanism small and inside a tool already in daily use (`qrispy`, the guard hook, a template field), start it as a warning, and write a separate tool only as a last resort: a separate tool that is right in intent but too costly to keep current goes unused.

## Project Roadmap

A project that runs several tickets toward one result (a paper, a system) keeps one `ROADMAP.md` next to its ticket root, so that every session can see where the project is going and what each ticket serves. Template: `skills/ticket/templates/ROADMAP.md` in the plugin.

**Structure.** The file has a short front part, read by every new ticket, and a ledger, read one section at a time when needed.

| Part | Section | Content |
|---|---|---|
| head | status line, source ticket, venue for a paper | |
| front | `## 방향` | one paragraph: what the project finds out or builds |
| front | `## 예상 결과물` | what exists when it is done (for a paper: chapter layout and key figures) |
| front | `## 범위와 제외` | what is in, and what is explicitly out |
| front | `## 완료 기준` | when the project is finished |
| front, paper | `## 주장의 형태` | prose only; anything with a status (for example a table reading earlier records) belongs in the ledger |
| ledger | `## 항목`, or for a paper `## 주장` and `## 실험` | one row per item |
| ledger | `## 틈` | what must be closed before finishing, with the owning ticket |
| ledger | `## 결정` | one sentence per decision and the Q item that made it; the reasoning stays in that Q item |
| ledger | `## 위험` | risk, the signal that shows it, the response |

Keep the head and front part under 40 lines and 4 KB.

**IDs** are words with a number: `Item-n` (general), `Claim-n` and `Exp-n` (paper), `Gap-n`, `Decision-n`, `Risk-n`; a sub-item adds a letter (`Exp-1a`). An ID is never reused. An item that is abandoned keeps its row with status `dropped`.

**Ledger columns** per section (as in the template): `## 항목` and `## 틈`: `ID | 내용 | 상태 | 담당 | 갱신`; `## 주장` adds `증거 층` and `증거` before `상태`; `## 실험` adds `방법` and `자원` (GPU or not). `## 결정` (`ID | 결정 | 원천 Q`) and `## 위험` (`ID | 위험 | 드러나는 신호 | 대응`) have no status: a decision that is replaced gets a new `Decision-n` row and the old row says `Decision-m으로 바뀜`; a risk that no longer applies says so in its `대응` cell. Neither is ever deleted. A migration that changes every row may record itself once in the ledger header instead of in each `갱신` cell. Columns: `담당` is the owning ticket (`<SYSTEM> NNN`); `갱신` is the date and the ticket that last changed the row (`YYYY-MM-DD <SYSTEM> NNN`). A claim row adds `증거 층` and `증거`; `증거` names a citable `CITE.md` row or says `새 증거 필요: Exp-n`. Evidence is a column, not a status. Do not write status as parenthetical prose inside a cell.

**Status values** (read by `qrispy`; aligned with the ticket triage values):

| Value | Meaning |
|---|---|
| `planned` | decided, not started (no owning ticket yet, or the owner is still in Q) |
| `active` | the owning ticket is working on it |
| `done` | achieved; the evidence is in the owning ticket's closeout (the owner closed `closed-completed`) |
| `parked` | on hold; the row says what reopens it (same meaning as triage `parked`) |
| `dropped` | will not be done; the row says why (a user decision, or the owner closed `closed-superseded`) |

**Ownership.**
- The front part changes only by a user decision recorded as a Q item in the ticket that changes it; the changed sentence gets `(<ticket> Q-n, <date>에 변경: …)`, and that ticket is reviewed before it closes.
- An existing ledger row is updated by its owning ticket (`상태`, `갱신`). Another ticket that needs a change tells the owner (a message to its `session`, or a Q item) instead of editing the row.
- Any ticket may add a row, with its basis (a user decision or note) in the row. An agent proposes a new row as a Q question when the ticket's result will be part of the project's outputs; it does not add one on its own.

**Linking tickets.** A ticket of a project with a `ROADMAP.md` names what it serves in `ticket.md` (`- 받치는 항목: Claim-2, Exp-1a, Gap-1`) and in `state.json.roadmap_items`. A ticket that serves no item (tool work, a deployment fix, a short exploration) writes `- 받치는 항목: 없음 — <reason>` and `state.json.roadmap_note`. Closed tickets are not back-filled; the ledger's `담당` column points to them. `qrispy show` lists a ticket's items with their status; `qrispy lint` warns about an ID that does not exist or is `dropped`, about an open ticket with neither field, about a `ticket.md` line that names other items than `roadmap_items`, and about `roadmap_items` that is not a list; repo lint warns about a status value outside the five, about a `담당` ticket that does not exist, and about a ledger row whose owning tickets are all closed while the row is still `planned` or `active`.

**Projects without a roadmap.** A project that keeps its direction in older documents instead of a `ROADMAP.md` lists in `<ticket root>/METHOD_LOCAL.md` where each roadmap role lives.

## Worktrees

Use a git worktree only when two or more sessions change code in the same repository at once. Name it `<repo>-wt/<ticket>` with branch `wt/<ticket>`. Commits on `wt/*` branches need no permission (the guard hook allows them); merging or rebasing into main needs the user's permission, and main itself is never rebased. Ticket documents in this repository do not need worktrees, because tickets live in separate directories.

## Orchestration

Several tickets run at once in three shapes: siblings that do not depend on each other, a parent with children, and a parent whose children are siblings. Siblings need no orchestrator: `deps`, the GPU lock and `qrispy inbox` are enough. A parent with two or more children running at the same time is run by the session that owns the parent, following the `qrispy:orchestrate` skill; there is no standing orchestrator session.

- **Relation.** Only the child writes `state.json.parent` (see State File). The parent's `p_plan.md` lists its children; each child's `ticket.md` names the parent ACs it serves. The parent reads a child's `z_closeout.md` and `CITE.md`, never its working files, and closes only when every child is closed or superseded.
- **Workers** (`qrispy worker`). Short, bounded work whose result is one document runs headless (`claude -p`, `codex exec`, `gemini <prompt>`) under `qrispy job run`; a headless worker edits nothing, because nobody can answer its permission dialogs, and the parent files its answer. Long work the user may want to join runs as a Claude background session (`claude --bg -n <system-nnn>`, joined with `claude attach`), or, for an agent without such sessions, in a window of tmux session `agents`. Workers that change the same code at the same time each get a git worktree (Worktrees). Workers run with this repository's settings and the user's normal permission mode; no flag that widens permissions is passed. A Claude background session starts only in a workspace Claude Code trusts (this repository or its worktrees). By default Claude Code moves a background session into its own worktree before it may Edit or Write in a git repository; the repository turns that off (`"worktree": {"bgIsolation": "none"}` in `.claude/settings.json`), so background workers edit the main checkout like interactive sessions and ticket files stay on main.
- **Reports.** A worker sends status lines `<ticket> <state>: <one line>`, state `working`, `blocked`, `needs-decision`, `done` or `failed`: Claude workers by `SendMessage` to the parent session, other agents by appending to `<child>/jobs/worker/status.log`, headless workers at the end of their answer. The parent waits on Claude background workers with `qrispy worker watch` (it wakes on a worker at a permission dialog, a finished turn, a vanished worker, or the five-minute heartbeat; `notify_when_idle` alone misses a worker stopped at a dialog) and on jobs with `qrispy job wait --heartbeat`. `claude agents --json` (shown by `qrispy show`, `ls --tree`, the dashboard and `qrispy worker status`) tells whether a worker runs and whether it waits at a permission dialog; such a worker is reported to the user at once. Workers are never restarted automatically.
- **Decisions**. The user may answer in any session. The session that receives a decision writes it verbatim into the `q_questions.md` of the ticket it belongs to, and tells that ticket's parent session in one line. Before acting, an orchestrator re-reads the child's `state.json` and `q_questions.md`.
- **GPU lock**. The machine's one GPU has one lock, `~/.agent_locks/gpu.json`, read and written by `qrispy lock`: `running` (a job under the lock is alive), `held` (between runs; the owner keeps it, e.g. a simulator stays up), free, or `ownerless` (the job vanished without `DONE.json`, or the holding session is gone and the lock silent for over 2 hours). `take` by another owner is refused with exit code 3 and the caller asks the user; it never blocks a process. `qrispy job run --gpu <kind>` takes it before a job and sets it back to `held` after; a procedure that keeps a GPU process up between jobs (named in `<ticket root>/METHOD_LOCAL.md`) takes it after start and releases it at shutdown. Only the user decides to delete an ownerless lock (`release --force`).
- **Scoped go**. A ticket may record, as a Q item, a go the user gave for a range of GPU runs, copied into `state.json.go_scopes`: `[{"q": "Q-7", "kind": "sim", "what": "…", "max_hours": 6, "max_runs": 8, "out": "research/…/results/…", "until": "YYYY-MM-DD"}]`. A run launched with `qrispy job run --go "<ticket> Q-n"` inside the remaining hours, runs and date needs no new question; `qrispy show` prints what is used, `qrispy lint` checks the fields. Anything outside a scope asks, as before.
- **Questions on one page**. `qrispy questions --tree <parent> [--html <file>]` gathers every unanswered Q item of a ticket and the tickets under it (an empty `> 사용자 답:` line) onto one `qrispy:plan-page` decision page, grouped by ticket; the receiving session records each answer in the ticket its card names.
- **Away**. `qrispy worker away on [--until HH:MM]` / `off` keeps `~/.agent_locks/away.json`. While the user is away, workers are told to stop after their current step and not to ask or notify, `watch` and `qrispy job wait` wake nobody (events go to `away_events.log` for one summary on return), and `qrispy lock take` refuses new GPU runs, even inside a scoped go.
- **Must not.** An orchestrator does not decide research questions for the user, does not start a GPU run outside a scoped go or take over another ticket's lock, does not commit on main (workers may commit on their own `wt/*` branch), does not edit a child's files, and does not ask a worker to do what its own permissions block.

## Regression Tests

A regression is a result that used to be right and silently changes after a code edit. A regression test is a fixed small input set (recorded bags or logs, pinned by sha256 in a manifest), the analysis/scoring command, and an `expected.json` (the trusted reference; software testing calls it a golden file), in the folder and with the runner that the repository names in `<ticket root>/METHOD_LOCAL.md`. When an analysis or scoring script changes, its regression test must reproduce `expected.json` before any cohort is re-scored with it. It needs no GPU. A changed expected value is a finding to explain, never a file to overwrite silently. Pin the data only, never the analysis code: the code is what the test checks.

## Within-Ticket Review & Revision

A review is an adversarial audit of a ticket's recorded evidence against its
stated claims and acceptance criteria — "does the recorded artifact support the
stated sentence" — not a general quality checklist. A review is required before:

- closing a ticket whose results feed a paper claim or another ticket's design;
- applying any W-gated writing-plan change the ticket proposes;
- or on user request.

Short or QRISPY-lite tickets with no claim-facing output do not need one.

### The review pass (`revN.md`)

Each review round N produces `revN.md`. The review pass is **read-only**: it
audits the artifacts and code as recorded, in a fresh context (against the
artifacts, not the memory of building them), and modifies nothing. A review
contains:

- an executive verdict (ticket may close / stays open, and why);
- the evidence reviewed, with exact paths (ticket record, deployed code, result
  artifacts, recorded bags);
- findings, each graded **blocking** (invalidates a claim or an acceptance
  criterion) or **advisory** (labeling, wording, robustness nice-to-have);
- an acceptance-criteria audit table (met / partly met / not met, with reason);
- a recommended correction and verification order;
- the verification commands actually run, with their results;
- a **claim-safe conclusion**: the narrower statement the current evidence
  supports. This is the sentence the writing plan is allowed to use until
  corrections land.

Since v2 the reviewer also checks intent: it reads `ticket.md`, the Q answers and `i_design.md` as the intent contract, compares them with each slice note's "Deviation from design" section, and grades any departure that is not recorded there as **blocking**. Each finding carries a mistake class (`rule-violation`, `missing-knowledge`, `unrecorded-drift` or `record-mismatch`, see Lessons) so the worker can enter it in `<ticket root>/LESSONS.md`.

### The response pass (`revN_response.md`)

Every review gets a response before corrections begin. The response maps every
finding to an action — nothing is silently dropped; each finding is accepted, or
rejected with a stated reason. It contains:

- a finding → correction map with per-item status;
- corrections clustered by resource gate: repo-local work runnable now vs
  sim/GPU work queued behind explicit user go;
- measurable pass gates in front of expensive re-runs (e.g. "diag rate ≥ 49 Hz
  before any F3 re-sweep") — never relaunch a sweep that would only reproduce a
  known-broken configuration;
- user decisions the findings require, resolved and recorded like Q-stage
  answers;
- a "what is explicitly NOT changed" guardrail list.

### Revision discipline

- Corrected outputs land as **new** artifacts with rev-suffixed names
  (`*_rev1.json`, `fig_*_rev1.pdf`, boot ids `*_RV1`); superseded artifacts stay
  on disk, marked withdrawn / do-not-cite. Never overwrite the evidence the
  review audited.
- When the review independently recomputed a number, cross-validate the
  corrected analyzer against that recompute and record the agreement.
- While any blocking finding is open: `z_closeout.md` is downgraded to
  provisional (see Closeout), the W-gated writing-plan change stays unapplied,
  and `state.json.current_stage` is set to `revN-correction`.

### Exit

The review loop ends — and the ticket may close — when every blocking finding is
resolved or explicitly waived by the user. Advisory findings may be carried into
the closeout's limitations or the next ticket's handoff.

## Closeout

`z_closeout.md` is the final ticket record. It should include:

- final status and close date;
- delivered scripts/docs/artifacts;
- final deliverable path;
- important findings;
- claim or acceptance-criteria alignment;
- known limitations;
- next-ticket handoff.

The closeout should not duplicate every detailed table from slice notes. It should
be the durable summary a future reader can use to understand what was delivered and
what remains.

### Provisional closeout

A `z_closeout.md` may exist while the ticket is still open — written as a
handoff draft, or downgraded by a review with blocking findings. A provisional
closeout MUST carry a status banner at the top, for example:

```text
> **PROVISIONAL** (2026-07-17) — rev1 blocking findings open; see
> `rev1_response.md`. Claim-safe conclusion in rev1 §15 applies until corrected.
```

and `state.json` must show the matching in-progress stage (e.g.
`revN-correction`). The presence of `z_closeout.md` alone never means the
ticket is closed; only `state.json` says that. Remove the banner (or replace the
closeout) when the ticket actually closes.

## Final Deliverables

If a ticket produces a report, benchmark summary, experiment note, or other
primary artifact, create a named deliverable file near the work product and point
to it from both `ticket.md` and `z_closeout.md`.

Example:

```text
research/<topic>/TICKET_002_DELIVERABLE.md
```

The ticket closeout can summarize the deliverable, but the deliverable itself is
the document that downstream writing or experiment planning should cite.

## Cross-Repo Ticket References

Bare `ticket NNN` is unambiguous only inside the repo that owns the ticket
system. Other repositories keep their own numbered tickets, and the numbers collide.

- Write a bare `ticket NNN` only inside the repo that owns that ticket system.
  Every reference from another repo — code comments, commit messages,
  CMakeLists, CONTEXT.md and other docs — must carry the owning system's
  prefix:
  - every system, this repo's and another repo's: `<SYSTEM> ticket NNN` (short form `<SYSTEM>-NNN`), with the system names of `qrispy.json`;
- The rule is symmetric: this repo's ticket docs referencing an external
  stack's ticket must prefix it too (`<SYSTEM> ticket NNN`), never bare.
- In durable documents (deliverables, closeouts, CONTEXT.md), give the full
  slug or path on first reference, e.g.
  `<SYSTEM> ticket NNN-<slug>`.

## Ticket Revisit

A revisit reopens a parked or closed ticket when upstream evidence or design has
changed but the ticket's deliverable has not.

**Reopen vs new ticket:** same deliverable, changed evidence/design → reopen as
a revisit. Changed scope or a new deliverable → open a new ticket with a handoff
from the old closeout.

**Two tiers of post-close change (pick with one test).** *Does the change touch
the final deliverable, a paper-facing claim or novelty verdict,
a document the repository lists in `<ticket root>/METHOD_LOCAL.md`, or a downstream ticket's input?*

- **Yes → revisit** (heavyweight): reopen the ticket, write `<stage>_revisit.md`,
  re-confirm stale Q decisions, and review before re-close; the re-close bumps
  `rev N → N+1`. Follow the rules below.
- **No → addendum** (lightweight, for-the-record: numerical verification,
  attribution *restatement* that changes no verdict, cross-links, learning
  notes): the ticket **stays `closed`**, no review round runs, and the change
  carries an in-body "post-closeout, non-reopening" banner. An addendum must not,
  by itself, alter a claim sentence or a novelty verdict — if it would, it is a
  revisit.

**Both tiers are logged, append-only, in `state.json`.** Every post-close change
— revisit or addendum — appends one entry to a `post_closeout` array (schema in
State File). This is what lets a closed ticket carry multiple revisits and
addenda over time while `state.json` stays the single source of truth for its
current state; the narrative detail stays in the ticket files
(`<stage>_revisit.md`, the in-body banner, `z_closeout.md`), never only in
`state.json`.

Rules for a revisit:

- **Record the trigger.** The revisit design opens with what prompted reopening
  (which ticket's result, which review directive) and what changed since the
  ticket was parked.
- **Supersede, don't overwrite.** Write `<stage>_revisit.md` (usually
  `i_design_revisit.md`) stating what it supersedes, what carries over
  unchanged, and the gates before execution. The original stage file stays on
  disk.
- **Re-confirm stale Q decisions.** List which earlier user decisions must be
  re-asked at kickoff; a reopened ticket does not silently inherit decisions
  made under obsolete assumptions.
- **Pre-register when consuming upstream-tuned results.** If the revisit uses
  parameters or arms selected in an upstream ticket, fix them a priori in the
  revisit design and pre-register the predictions before any run — revisit runs
  are held-out confirmation, not tuning.
- **Update `state.json`:** append a `post_closeout` entry with `kind: revisit`,
  set status back to `open`, and mark `current_stage` as a revisit (e.g.
  `I (revisit)`). Slice numbering continues from where the ticket left off; do
  not restart at 0.

## State File

Use `state.json` with at least:

```json
{
  "ticket_slug": "NNN-ticket-slug",
  "current_stage": "closed",
  "last_approved_stage": "Q",
  "next_action": "Open the next ticket for ...",
  "slices_completed": [1, 2],
  "slices_total": 2,
  "created": "YYYY-MM-DD",
  "updated": "YYYY-MM-DD"
}
```

For active tickets, `current_stage` may be `Q`, `R`, `I`, `S`, `P`, `Y`, or a more
specific in-progress label. For finished tickets, use `closed`.

Since v2 an active ticket also keeps these fields current; every session that works on the ticket updates them before it ends:

```json
{
  "awaiting_user": ["one short line per decision or approval the user owes"],
  "drift": [{"slice": 2, "kind": "requirement", "q": "Q-18", "summary": "one line", "approved_by": "user 2026-10-14"}],
  "lesson_refs": ["L-NNN"]
}
```

Optional `roadmap_items` (list of ledger IDs) and `roadmap_note` (one line, when the ticket serves no item) link the ticket to its project's `ROADMAP.md` (see Project Roadmap).

Optional `go_scopes` lists scoped gos for GPU runs (see Orchestration).

Optional `parent` names the ticket this one is a part of, as `"<SYSTEM> NNN"` (another system is allowed). Only the child writes it; a parent's children are whatever tickets name it, so the two sides cannot disagree, the same direction as `deps`. `qrispy show` lists a ticket's parent and children with their owning sessions and whether those sessions run, `qrispy ls --tree` draws project → parent → child, and `qrispy lint` warns about a parent that does not exist, a loop, an open child under a closed parent, and a closed parent with an open child. A ticket that wrote a slug or a path instead is read as the same ticket, and an open ticket is asked to use the new form.

Optional `session` holds the name of the agent session that currently owns the ticket, so other sessions can message it directly, and optional `session_id` that session's id; both come from `qrispy worker whoami`. A session's name changes when it reopens but its id does not, so `qrispy show`, `ls --tree`, the dashboard and `qrispy worker status` look the id up in `claude agents --json` and show the name it has now (`old → now new`); send to that name. `awaiting_user` is empty when nothing is owed; `qrispy inbox` collects it across tickets. `drift.kind` is `requirement` or `discovery` (see Drift). Keep `state.json` under 8 KB: stage results and narrative belong in the ticket's Markdown files (`qrispy lint` checks this for v2 tickets; several pre-v2 files grew past 80 KB). An optional `lint_ignore` list names ticket files that `qrispy lint` should not style-check because the agent did not write them (for example a pasted source document).

### Cross-ticket dependencies (`deps`)

Dependencies are written by hand and argued in the ticket; no tool checks them (no cycle, blocked-upstream or pin check). `qrispy show` lists a ticket's `deps`, and `qrispy inbox` collects those of kind `user_gate`.

An **active** ticket declares its own **incoming** edges — always from the
dependent side, never the producer's:

```json
{
  "deps": [
    {"on": "015", "kind": "gates_close", "note": "what must land there, and why"}
  ]
}
```

`kind` is one of:

| kind | blocking | meaning |
|---|---|---|
| `blocks_now` | yes | upstream blocks current work |
| `gates_close` | yes | upstream must land before this ticket can close |
| `user_gate` | yes | upstream carries a pending user decision |
| `input` | no | consumed upstream output (normally already closed) |
| `instrument` | no | upstream **code this ticket runs**, not a finding it cites |
| `dataset` | no | a shared **cohort/dataset** this ticket builds on |
| `external` | no | a **commit in another repo** |
| `directional` | no | informs, non-blocking |

Invented kinds are rejected — put the nuance in `note`, not in a new kind name.
A gate that has since cleared becomes `input`; it is not a new kind.

**`instrument` edges must be pinned.** A cited finding and an executed script
decay differently: a finding in a closed ticket is frozen by supersession
discipline, but shared code (e.g. `research/theory/.../certified_sets.py`, which
one ticket runs and another produced) lives outside any ticket directory and anyone
may edit it. Numbers computed with a changed instrument silently change meaning,
so record the bytes you built on:

```json
{"on": "039", "kind": "instrument",
 "pin": {"research/theory/capture_basin/verification/certified_sets.py": "<sha256>"},
 "note": "Cut F / Cut I methods; PLACEHOLDER_THETA is what this ticket replaces"}
```

Compute a pin by hand (`sha256sum <file>`; for a commit, `git -C <repo> rev-parse HEAD`) and argue the dependency in the ticket. Re-binding a pin is a deliberate separate act asserting the results still hold, not a way to silence a finding.

`dataset` works identically; pin the cohort manifest. It exists because a shared
cohort can be invalidated wholesale, which moves every downstream consumer at once.

**`external` edges** name a commit in another repo instead of a ticket here, so
`on` is a free-form ref (`<repo>#017`, `<repo>#recorder`) and the pin is a repo plus a
commit:

```json
{"on": "<repo>#017", "kind": "external",
 "pin": {"repo": "/path/to/<repo>", "commit": "b2ddf31"},
 "note": "what was deployed for the cohort this ticket analyses"}
```

A pinned commit that is **gone** (rebased, force-pushed or GC'd) orphans the revision the evidence was produced at; one that is valid but no longer an ancestor of that repo's HEAD deserves a note in the ticket.

`deps` supersedes the older ad-hoc keys (`blocked_by`, `depends_on`, `blocks`,
`hard_deps`/`soft_deps`, `parents`, `consumes`, `feeds`). Migrate a ticket by
replacing them, so a live edge is written in exactly one place.

To see the state of all tickets at once, use the read-only `qrispy ls` and `qrispy inbox`; they report, they never gate.

Tickets that go through review or revisit rounds add:

```json
{
  "reviews": [
    {
      "review": "rev1.md",
      "response": "rev1_response.md",
      "verdict": "stays open",
      "blocking_open": 0,
      "date": "YYYY-MM-DD"
    }
  ],
  "post_closeout": [
    {
      "seq": 1,
      "kind": "revisit",
      "date": "YYYY-MM-DD",
      "trigger": "026 FINAL closeout + reviewer directive",
      "scope": "what changed",
      "changes_deliverable": true,
      "review": "rev2.md",
      "status_after": "closed (rev 2)"
    },
    {
      "seq": 2,
      "kind": "addendum",
      "date": "YYYY-MM-DD",
      "trigger": "user: for-the-record verification",
      "scope": "what was added",
      "changes_deliverable": false,
      "review": null,
      "status_after": "closed (rev 2)"
    }
  ]
}
```

`post_closeout` is an **append-only** log (it supersedes the old scalar
`reopened` field) — one entry per post-close change, so a closed ticket can carry
any number of revisits and addenda in order. Each entry is either a `revisit`
(reopened, reviewed, bumps `rev N → N+1`) or an `addendum` (stays `closed`, no
review). A workflow-wide migration addendum may use the compact form `{date, kind: "addendum (non-reopening)", by, note}`; a reader treats any `kind` that starts with `addendum` as an addendum. Keep both `reviews` and `post_closeout` entries compact — verdicts,
scope one-liners, dates; the narrative detail belongs in the `revN*.md` /
`<stage>_revisit.md` / `z_closeout.md` files, not in `state.json`. During review
corrections, `current_stage` is `revN-correction`; during a revisit, mark the
stage as such (e.g. `I (revisit)`). A ticket may move to `closed` only when
`blocking_open` is 0 in every review entry (or the user has explicitly waived the
remainder).
