# Method history

The kit's method files (`QRISPY_METHOD.md`, `DEV_REVIEW_RECIPE.md`, `REVIEW_PROMPT.md` in this folder) carry no ticket references in their text, because they are read from many repositories. This file keeps those references: one row per reference removed from the text, naming the passage as it now stands and the ticket, review finding, Q item or lesson it came from. Every origin below is in the repository where QRISPY was developed (ticket systems `RAL`, `THESIS` and `PAPER1`); references are written in full (`RAL ticket 084 Q-31`) so that they stay unambiguous elsewhere. When a later lesson is added to a method file, add its origin here.

## QRISPY_METHOD.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| QRISPY Ticket Method | heading v2 changes | RAL ticket 084 (QRISPY v2, 2026-10-14) |
| QRISPY Ticket Method | ticket directories `<ticket root>/<SYSTEM>-<NNN>-<ticket-slug>/`; the older `<NNN>-<ticket-slug>/` still read, warned on by `qrispy lint --repo` | kit change of 2026-11-10 (the user's request in the Simulation repository, system SIM; no ticket) |
| File Registry | row `jobs/<id>/` | RAL ticket 087 (GPU and scoped-go fields of `job.json`) |
| File Registry | row `jobs/<id>/` | RAL ticket 087 (`jobs/worker/status.log`) |
| File Registry | row `evidence/` | RAL ticket 084 rev2 R2-A4 |
| File Registry | row `qrispy.json` (repository root) | RAL ticket 089 (`qrispy.json`) |
| File Registry | row `qrispy config` (`lib/qrispy_config.py` in the plugin) | RAL ticket 089 (`evidence/jobs_portable_macos.txt`, `evidence/jobs_portable_linux.txt`) |
| File Registry | row `<project>/ROADMAP.md` | RAL ticket 086 (project roadmaps) |
| Required Files | Short or QRISPY-lite tickets may omit `r_research.md` and `s_structure.md` when they add no value. `z_closeout … | RAL ticket 084 S6 (2026-10-15) |
| Drift | **Discovery** — started by the agent: the design does not work as written and the method must change. The agen … | RAL ticket 084 Q-34 |
| Lessons | The agent records an entry, unasked, in the same turn when the user corrects it, when a review finds a defect … | RAL ticket 084 Q-26 |
| Project Roadmap | A project that runs several tickets toward one result (a paper, a system) keeps one `ROADMAP.md` next to its t … | RAL ticket 086 |
| Orchestration | Several tickets run at once in three shapes: siblings that do not depend on each other, a parent with children … | RAL ticket 087 (orchestration shapes) |
| Orchestration | Several tickets run at once in three shapes: siblings that do not depend on each other, a parent with children … | RAL ticket 087 Q-2 |
| Orchestration | **Workers** (`qrispy worker`). Short, bounded work whose result is one document runs headless (`claude -p`, `c … | RAL ticket 087 Q-5 |
| Orchestration | **Workers** (`qrispy worker`). Short, bounded work whose result is one document runs headless (`claude -p`, `c … | RAL ticket 087 Q-10 |
| Orchestration | **Workers** (`qrispy worker`). Short, bounded work whose result is one document runs headless (`claude -p`, `c … | RAL ticket 087 Q-14 |
| Orchestration | **Decisions**. The user may answer in any session. The session that receives a decision writes it verbatim int … | RAL ticket 087 Q-1 |
| Orchestration | **GPU lock**. The machine's one GPU has one lock, `~/.agent_locks/gpu.json`, read and written by `qrispy lock` … | RAL ticket 087 Q-6 |
| Orchestration | **GPU lock**. The machine's one GPU has one lock, `~/.agent_locks/gpu.json`, read and written by `qrispy lock` … | RAL ticket 087 Q-11 |
| Orchestration | **Scoped go**. A ticket may record, as a Q item, a go the user gave for a range of GPU runs, copied into `stat … | RAL ticket 087 Q-7 |
| Orchestration | **Scoped go**. A ticket may record, as a Q item, a go the user gave for a range of GPU runs, copied into `stat … | RAL ticket 087 Q-12 |
| Orchestration | **Questions on one page**. `qrispy questions --tree <parent> [--html <file>]` gathers every unanswered Q item … | RAL ticket 087 Q-15 |
| Orchestration | **Away**. `qrispy worker away on [--until HH:MM]` / `off` keeps `~/.agent_locks/away.json`. While the user is … | RAL ticket 087 Q-16 |
| Regression Tests | A regression is a result that used to be right and silently changes after a code edit. A regression test is a … | RAL ticket 084 Q-29 (named "golden replay" until 2026-10-15) |
| Within-Ticket Review & Revision | Canonical examples: tickets 024 (`rev1.md`) and 026 (`rev1.md`/`rev2.md` with | RAL ticket 024 (`rev1.md`, canonical review example) |
| Within-Ticket Review & Revision | Canonical examples: tickets 024 (`rev1.md`) and 026 (`rev1.md`/`rev2.md` with | RAL ticket 026 (`rev1.md`, `rev2.md` with responses, canonical review example) |
| Ticket Revisit | changed but the ticket's deliverable has not. | RAL ticket 019 (canonical revisit example) |
| Ticket Revisit | changed but the ticket's deliverable has not. | RAL ticket 026 (its final closeout reopened RAL ticket 019) |
| Ticket Revisit | from the old closeout. | RAL ticket 026 (spun off from RAL ticket 023) |
| State File | Optional `roadmap_items` (list of ledger IDs) and `roadmap_note` (one line, when the ticket serves no item) li … | RAL ticket 086 (`roadmap_items`, `roadmap_note`) |
| State File | Optional `go_scopes` lists scoped gos for GPU runs (see Orchestration). | RAL ticket 087 Q-7 (`go_scopes`) |
| State File | Optional `parent` names the ticket this one is a part of, as `"<SYSTEM> NNN"` (another system is allowed). Onl … | RAL ticket 087 Q-4 |
| State File | Optional `session` holds the name of the agent session that currently owns the ticket, so other sessions can m … | RAL ticket 084 Q-30 |
| State File | Optional `session` holds the name of the agent session that currently owns the ticket, so other sessions can m … | RAL ticket 087 Q-17 |
| Cross-ticket dependencies (`deps`) | one ticket runs and another produced) lives outside any ticket directory and anyone | RAL ticket 050 (runs `certified_sets.py`) |
| Cross-ticket dependencies (`deps`) | one ticket runs and another produced) lives outside any ticket directory and anyone | RAL ticket 039 (produced `certified_sets.py`) |
| Cross-ticket dependencies (`deps`) | cohort can be invalidated wholesale, which moves every downstream consumer at once. | RAL ticket 019 revisit2 (07-21 cohort reclassified PRE-FIX) |
| Cross-ticket dependencies (`deps`) | review). A workflow-wide migration addendum may use the compact form `{date, kind: "addendum (non-reopening)", … | RAL ticket 084 S5 (added `CITE.md` to 27 closed tickets) |
| Cross-ticket dependencies (`deps`) | review). A workflow-wide migration addendum may use the compact form `{date, kind: "addendum (non-reopening)", … | RAL ticket 084 rev1 A-11 |

## REVIEW_PROMPT.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| The contract | This ban exists because a reviewer tampered with its `/tmp` mirror | RAL lesson L-001 (`tickets/LESSONS.md`, incident of 2026-08-05) |
| The contract | This is enforced, not trusted. You run as the `qrispy:reviewer` subagent, with the file-editing tools removed, … | RAL ticket 084 (review enforced by tools, not trust) |
| The contract | This is enforced, not trusted. You run as the `qrispy:reviewer` subagent, with the file-editing tools removed, … | RAL ticket 084 Q-18 (`tickets/handshake.sh` retired 2026-10-14) |
| The contract | This is enforced, not trusted. You run as the `qrispy:reviewer` subagent, with the file-editing tools removed, … | RAL ticket 084 rev3 R3-A3 |
| The contract | mtimes against other active tickets. | RAL BUG 001 |
| Grading discipline | Check intent, not only evidence (QRISPY v2). The intent contract is `ticket.md` (ACs), the answers in `q_quest … | RAL ticket 084 (QRISPY v2 intent check) |

## DEV_REVIEW_RECIPE.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 067 rev1–rev3 (added §L) |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 015 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 017 rev1–2 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 021 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 023 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 026 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 033 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 034 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 036-pm |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 036-DUAL rev1–5 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 038 rev1–4 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 040 rev1–2 |
| Development & Review Recipe (how our development and review rounds fail) | **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes). | RAL ticket 041 rev1–2 |
| A. Supersession & lineage §A1 | one review (the ticket declared the corrected result set canonical in | RAL ticket 041 rev2 R2-F1 |
| A. Supersession & lineage §A1 | same class as an earlier lineage single-valuedness finding. **Checklist when | RAL ticket 038 rev2 |
| A. Supersession & lineage §A2 | CURRENT producer, never patched or reinterpreted.** In one review the analyzer was | RAL ticket 038 rev3 |
| A. Supersession & lineage §A2 | analyzer. Another ticket applied the lesson correctly (full from-bags re-run, not an | RAL ticket 041 rev1 |
| A. Supersession & lineage §A3 | One ticket kept `s1_report.json` byte-identical, marked | RAL ticket 040 rev1 F7 |
| A. Supersession & lineage §A3 | SUPERSEDED-do-not-quote; another's `WITHDRAWN_COLUMNS.md` names the four corrupted | RAL ticket 041 (`WITHDRAWN_COLUMNS.md`) |
| A. Supersession & lineage §A3 | *cannot* overwrite shipped evidence (`S4_OUT`). Suffix semantics: | RAL ticket 041 (`S4_OUT`) |
| A. Supersession & lineage §A3 | *cannot* overwrite shipped evidence (`S4_OUT`). Suffix semantics: | RAL ticket 060 rev5 L1 |
| A. Supersession & lineage §A3 | if a file instead carries the number of the review round that forced it (for example | RAL ticket 060 (`WAVE3_SCORING_rev4.md`) |
| A. Supersession & lineage §A4 | rather than bound as if clean (one ticket re-scoped its manifest | RAL ticket 041 rev2 R2-F2 |
| A. Supersession & lineage §A4 | rather than bound as if clean (one ticket re-scoped its manifest | RAL ticket 033 rev3 |
| A. Supersession & lineage §A5 | record contradicts the resolution (one review: numerically complete, lineage | RAL ticket 041 rev2 |
| A. Supersession & lineage §A5 | (one ticket kept 3 open). Correct a premature claim by amendment, not erasure. | RAL ticket 038 rev3 |
| A. Supersession & lineage §A6 | before it doesn't.** One response answered an unbound-configuration finding with | RAL ticket 017 rev1 |
| A. Supersession & lineage §A6 | whole profile permanently UNVERIFIED; the next review found the two files whose sha256 | RAL ticket 017 rev2 |
| B. Review-round discipline §B1 | In one response the reviewer's corrected numbers were exact, but my | RAL ticket 041 rev1_response |
| B. Review-round discipline §B1 | of a binary flag where the defined semantic was the mean (fraction). In another review | RAL ticket 034 rev1 |
| B. Review-round discipline §B2 | One review's remaining-work table still recommended the "G ≈ 0.81 tracking" | RAL ticket 041 rev1 |
| B. Review-round discipline §B2 | wording its own F4 self-correction had withdrawn; another review audited a | RAL ticket 038 rev4 |
| B. Review-round discipline §B3 | Stamps are append-only (`PREDICTIONS_STAMP.md` addenda); acceptance goes | RAL ticket 041 (`PREDICTIONS_STAMP.md`) |
| B. Review-round discipline §B3 | into a provenance *addendum*, corrections into `revN_response.md` — the | RAL ticket 041 (provenance addendum) |
| B. Review-round discipline §B3a | deliverable while the response said it was fixed (the fifth recurrence of | PAPER1 ticket 004 rev3 B3-1 |
| B. Review-round discipline §B3a | one recorded lesson). `revN_response.md` therefore gives each finding of `revN.md` its own heading | RAL lesson L-019 (`tickets/LESSONS.md`) |
| B. Review-round discipline §B4 | **B4 — An abstract-level grade is not a novelty lock.** One ticket's Lemma A | RAL ticket 015 (Lemma A) |
| B. Review-round discipline §B5 | chain, not the sentence. A withdrawn or refuted item | RAL ticket 021 |
| B. Review-round discipline §B5 | is *recorded* (a review's own draft withdrawal of a finding is the model), never | RAL ticket 041 rev1 F4 |
| B. Review-round discipline §B6 | before writing.** In one ticket rev1 read `S4_FINDINGS.md` at | RAL ticket 060 rev1/rev2 (2026-08-12) |
| B. Review-round discipline §B6 | selector, not a binding"*. Rule: record `sha256sum` beside every quoted | RAL ticket 048 |
| B. Review-round discipline §B6 | if it moved, re-read and say so in the review's evidence section (an | RAL ticket 060 rev2 |
| C. Instruments & analyzers §C1 | **C1 — Bind array/message layouts by schema, not by counting.** In one review | RAL ticket 041 rev1 F1 |
| C. Instruments & analyzers §C2 | The index bug was caught precisely because the live covariate logger and | RAL ticket 041 |
| C. Instruments & analyzers §C3 | the discard recorded.** One ticket's xcorr-lag was discarded first for an incomplete | RAL ticket 041 |
| C. Instruments & analyzers §C3 | only after the clean-data result (non-causal lag in 27/32) matched another ticket's | RAL ticket 038 S2 |
| C. Instruments & analyzers §C4 | **C4 — Unit/ordering checks on scores, especially with ∞ or caps.** In one review | RAL ticket 038 rev1 P3 |
| C. Instruments & analyzers §C5 | before calling an implementation a reproduction; label adaptations.** One finding: | RAL ticket 026 F2 |
| C. Instruments & analyzers §C5 | an equation's sign/direction (Eq. 89); one ticket's arms were proxies, not literature classes, | RAL ticket 023 |
| C. Instruments & analyzers §C6 | × a 10 Hz tick); `yolo_result_vision` was a different message type | RAL ticket 036-pm |
| C. Instruments & analyzers §C6 | *also* breaking bag recording. | RAL ticket 041 S2 |
| D. Claims & pre-registration §D1 | **D1 — Stamp before any run; re-scope BEFORE the run, in the stamp.** One ticket's | RAL ticket 041 |
| D. Claims & pre-registration §D2 | a result.** One ticket's R-a ("gain debit shrinks every set" — it shrank none: | RAL ticket 041 |
| D. Claims & pre-registration §D3 | it; keep the refinement trail.** One slice went terminal-ε_v → early-transient → | RAL ticket 041 S4 |
| D. Claims & pre-registration §D3 | discarded intermediate instruments recorded (§C3). Another ticket's rate-not-range | RAL ticket 036-pm |
| D. Claims & pre-registration §D3 | correction and a third's mechanism-claim contraction are the same pattern: write | RAL ticket 033 |
| D. Claims & pre-registration §D4 | Hz…", never "the deployed system works"; adopt the review-issued | RAL ticket 041 Q1 |
| D. Claims & pre-registration §D4 | claim-safe sentence as the citable form until the next gate. | RAL ticket 040 rev2 §6 |
| D. Claims & pre-registration §D4 | Observation-layer/proxy results never become closed-loop | RAL ticket 041 rev2 §9 |
| D. Claims & pre-registration §D4 | discipline). | RAL ticket 023 |
| E. Concurrency & identity §E1 | flagging or reverting.** One review flagged a writing-plan edit that | RAL ticket 040 rev1 R1 |
| E. Concurrency & identity §E1 | belonged to a concurrent session (withdrawn by the user); another review's F1 was a | RAL ticket 038 rev4 F1 |
| E. Concurrency & identity §E2 | Two tickets can share a number (a phase-map ticket and a dual-control ticket did); a number was reused after | RAL ticket 036-pm and RAL ticket 036-dual (shared number 036) |
| E. Concurrency & identity §E2 | Two tickets can share a number (a phase-map ticket and a dual-control ticket did); a number was reused after | RAL ticket 041 (number reused) |
| F. The one-screen repeat-offender list | heading G. Added 2026-07-28 (paid by one ticket's S6 audit) | RAL ticket 041 rev4 (S6 audit) |
| G. Added 2026-07-28 §G1 | implementing code before any run.** One ticket stamped, ran, and reported a | RAL ticket 041 |
| G. Added 2026-07-28 §G2 | manifest that hashes it.** One ticket's first seal hashed `PROVENANCE.md`, then | RAL ticket 041 |
| G. Added 2026-07-28 §G3 | **G3 — A scalar error/uncertainty ratio is not a calibration test.** One ticket read | RAL ticket 041 |
| G. Added 2026-07-28 (paid by one ticket's S6 audit) | heading H. Added 2026-07-28 (paid by one falsification-gate slice) | RAL ticket 027 S4 / S4-B |
| H. Added 2026-07-28 §H1 | instances in one slice: | RAL ticket 027 S4 |
| H. Added 2026-07-28 §G4 | first, then grep-verify zero unmarked residues.** One ticket paid three review rounds | RAL ticket 041 rev2, rev5, rev6 |
| H. Added 2026-07-28 (paid by one falsification-gate slice) | heading I. Added 2026-08-02 (paid by one five-round contraction) | RAL ticket 036-DUAL rev1–rev5 |
| I. Added 2026-08-02 (paid by one five-round contraction) | **Ticket identity:** every "036" below is **036-DUAL** | RAL ticket 036-feedback-aware-dual-control-observability (036-DUAL; distinct from the 036 phase-map ticket) |
| I. Added 2026-08-02 §I1 | document-list half of the sweep and left the pattern-list half open. One ticket | RAL ticket 036-DUAL |
| I. Added 2026-08-02 §I2 | artifact, not a recomputation of it.** One ticket's manifest bound **14** hashes | RAL ticket 036-DUAL |
| I. Added 2026-08-02 §I3 | *not* cover. One drift-check record asserted the guard "binds what the | RAL ticket 036-DUAL |
| I. Added 2026-08-02 §I4 | tests `generated ⊆ shipped` is not symmetric.** One ticket replaced its grep sweep | RAL ticket 036-DUAL |
| I. Added 2026-08-02 (paid by one five-round contraction) | heading J. Added 2026-08-09 (paid by one ticket's five review rounds — six recurrences of one failure) | RAL ticket 061 rev1–rev5 |
| J. Added 2026-08-09 (paid by one ticket's five review rounds — six recurrences of one failure) | That ticket ran five review rounds, 19 blocking findings. **Six of them were the same | RAL ticket 061 |
| J. Added 2026-08-09 (paid by one ticket's five review rounds — six recurrences of one failure) | root, and it was paid again at the *prose* layer rather than the sweep layer. | RAL ticket 061 |
| J. Added 2026-08-09 §J1 | ABSENCE.** A `.msg` header asserted "an honest UPPER BOUND" twenty lines | RAL ticket 061 |
| J. Added 2026-08-09 §J2 | list of phrases.** The ticket built a standing 8-phrase × 8-file check at rev2 for | RAL ticket 061 |
| J. Added 2026-08-09 §J2 | vacuous — the ticket claimed that control in its record for a whole round before | RAL ticket 061 |
| J. Added 2026-08-09 §J3 | **J3 — A phrase ban catches copies, never rewords.** The sixth recurrence sat | RAL ticket 061 |
| J. Added 2026-08-09 §J4 | both survive until someone re-derives them. The ticket asserted a residual statistic | RAL ticket 061 |
| J. Added 2026-08-09 §J5 | evidence.** The ticket tested ~1700 (pairing-offset, sensor-sample) hypotheses per tick | RAL ticket 061 |
| J. Added 2026-08-09 §J6 | **J6 — Report the unexplained fraction FIRST, with its denominator.** The ticket drew a | RAL ticket 061 |
| J. Added 2026-08-09 (paid by one ticket's five review rounds — six recurrences of one failure) | heading K. Added 2026-08-11 (paid by one ticket's five diagnostic boots — four wave-corrupting defects in thre … | RAL ticket 060 (five diagnostic boots) |
| K. Added 2026-08-11 §K3 | the next one visible. The arrival-axis carry-over was invisible while the | RAL ticket 060 |
| K. Added 2026-08-11 §K4 | moment the value changes.** One ticket's item-10 checker hard-codes the expected arm | RAL ticket 058 (item-10 checker) |
| K. Added 2026-08-11 §K4 | configuration; a later ticket redefined that arm twice in one night, and the checker would | RAL ticket 060 |
| K. Added 2026-08-11 §K4 | code: a runbook names the one file that owns each value. | RAL ticket 060-law-axis-cohort (`RECIPES.md` §0) |
| K. Added 2026-08-11 (paid by one ticket's five diagnostic boots — four wave-corrupting defects in three days) | heading L. Added 2026-08-20 (paid by one ticket's rev1→rev3 — a false green that crossed a repo) | RAL ticket 067 rev1→rev3 |
| L. Added 2026-08-20 §L1 | shown to go red.** One ticket quarantined invalid bags by SUFFIX rename, then "confirmed" | RAL ticket 067 |
| L. Added 2026-08-20 §L2 | enumeration that enforces this needs an explicit scope.** Three consecutive rounds | RAL ticket 067 |
| L. Added 2026-08-20 §L2 | **Residual failure mode (added same day, paid by the next round's R4-B1 — the counter's own | RAL ticket 067 rev4 R4-B1 |
| L. Added 2026-08-20 (paid by one ticket's rev1→rev3 — a false green that crossed a repo) | heading M. Added 2026-08-29 (paid by one labelling defect surviving its own correction round) | RAL ticket 071 rev2→rev_ac7_1 |
| M. Added 2026-08-29 §M1 | **M1 — A finding names a defect CLASS, not a file.** One review ruled a | RAL ticket 071 rev2 B2-2 |

## Skills and the reviewer agent

The skills, their templates and the reviewer agent (`skills/` and `agents/` in this plugin) follow the same rule as the method files: their text carries no ticket references, and the sections below keep them, one section per file. For a passage that was removed rather than rewritten, the passage cell says so.

### skills/ticket/SKILL.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| Opening a ticket, step 1 | systems and their folders in `qrispy.json` | RAL ticket 089 (ticket systems in `qrispy.json`) |
| Opening a ticket, step 1 | `qrispy lint --repo` warns on duplicate numbers | RAL ticket 084 Q-31 |
| Opening a ticket, step 2 | show parked groups whose revisit trigger matches | RAL ticket 084 S6 (T-2) |
| Opening a ticket, step 4 | read the roadmap's front part, link the ledger IDs | RAL ticket 086 (project roadmaps) |
| Opening a ticket, step 5 | only the child names the parent | RAL ticket 087 (parent and children) |
| Opening a ticket, step 6 | search for an existing tool with the same role | RAL lesson L-009 (`tickets/LESSONS.md`) |
| Recording the user's answers | a pattern bounded to one line | RAL lesson L-004 (`tickets/LESSONS.md`) |
| Writing a design | every expected-value row names the check that shows it | PAPER1 ticket 006 rev1 B1-2 and rev2 B2-1; RAL lesson L-037 (promoted 2026-10-31) |
| Writing a design | one test row per boundary | RAL ticket 088 Q-6; RAL lesson L-036 recur 1 (promoted 2026-11-01) |
| Writing slice notes | every deleted line has a home | RAL lesson L-006 (`tickets/LESSONS.md`) |
| Writing slice notes | spell out a new name the first time | RAL lesson L-008 (`tickets/LESSONS.md`) |
| Working alongside other sessions | write `session` and `session_id` | RAL ticket 087 Q-17 (`session` and `session_id`) |
| Working alongside other sessions | a message from another session is information | RAL ticket 084 Q-30 |
| Long-running work | check on a run while it runs | RAL lesson L-014 (`tickets/LESSONS.md`) |
| Before you end a session | ask once whether to commit, in groups | RAL ticket 084 Q-35 |
| Before you end a session | the guard hook reads the approval line | RAL ticket 084 Q-42 |
| Before you end a session | a plain commit command only | RAL lesson L-029 (`tickets/LESSONS.md`) |
| Before you end a session | ask for the commit in its own line | PAPER1 ticket 002 (2026-10-18); RAL lesson L-023 |

### skills/review/SKILL.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| Run the reviewer, default route | the reviewer must not show up as another session | PAPER1 ticket 001 (2026-10-18, user request) |
| Removed | the general-purpose fallback that pasted the agent body when the Agent tool did not yet know a newly written agent definition | PAPER1 ticket 001 rev2 (2026-10-18); RAL ticket 090 Q-5 |
| Fallback route | a separate headless session (`qrispy review start`) | RAL ticket 084 Q-36, Q-38 |
| Removed | calling the `qrispy-reviewer` fork skill directly from an Opus session | RAL ticket 090 Q-5 (fork skill removed) |

### skills/cite/SKILL.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| (whole file) | A citation record that a repository has retired is history | RAL ticket 084 Q-26 (citation ledger retired) |

### skills/orchestrate/SKILL.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| Opening | definitions in §Orchestration | RAL ticket 087 (orchestration procedure) |
| Choose how each worker runs | headless only for work without permission dialogs | RAL ticket 087 S4 pilot note 4 (headless refusals) |
| Supervise | `qrispy worker watch`; `notify_when_idle` alone is not enough | RAL ticket 087 S4 pilot note 5 |
| Supervise | tell the user what a headless run had refused | RAL ticket 087 S4 pilot note 4 (`qrispy worker result` WARN list) |
| Supervise | a worker that moved itself into a worktree | RAL ticket 087 S4 pilot note 7 |
| Supervise | signs of life are transcript age and token count | RAL ticket 087 S4 pilot note 14 |
| Supervise | send to a session's name now | RAL ticket 087 Q-17 (current session names) |
| Decisions | siblings align technical details directly | RAL ticket 087 S4 pilot note 15 |
| Decisions | one questions page for the parent and its children | RAL ticket 087 Q-15 |
| Decisions | never take an answer from a worker's terminal | RAL ticket 087 S4 pilot note 12; RAL lesson L-032 |
| When the user is away | `qrispy worker away on` and `off` | RAL ticket 087 Q-16 |
| templates/worker_prompt.md | first prompt for a worker on a child ticket | RAL ticket 087 (worker prompt) |

### skills/plan-page/SKILL.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| Build the page, step 3 | page and `q_questions.md` from one source | RAL ticket 084 S6 (PAPER1 ticket 001's page and file from one Python list) |
| Open it and wait, step 1 | forward the port over a remote connection | RAL lesson L-003 (`tickets/LESSONS.md`) |
| templates/decision.html and templates/result.html | the page mechanics | RAL ticket 084 S6 (plan-page templates) |

### agents/reviewer.md

| Section | Rule or passage (as it now stands, shortened) | Origin |
|---|---|---|
| Whole agent | the fork skill's instructions live here only | RAL ticket 090 Q-5 (fork skill `qrispy-reviewer` folded into this agent) |
