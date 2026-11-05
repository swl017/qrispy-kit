# Development & Review Recipe (how our development and review rounds fail)

Cross-ticket catalogue of **development and review mistakes that have recurred
across sessions** — the sibling of `QRISPY_METHOD.md` (how we run
tickets) and the repository's own operating manuals (listed in its `METHOD_LOCAL.md`). The method files say
what to do; this file records the specific ways we have failed to do it, so the
next session recognizes the failure *before* paying for it again.

- **Status:** as-run — every rule below was paid for by a real defect in a real
  ticket, found by a review round or by a later session. Entries carry the
  ticket(s) that paid, listed in `HISTORY.md` beside this file.
- **Last verified:** 2026-08-20 (distilled from the review rounds of many tickets and the memory lesson notes).
- **How to use:** read §A before accepting any correction or declaring
  anything canonical; read §B before writing or responding to a `revN.md`;
  read §C before trusting an analyzer you (or anyone) wrote; read §D before
  stamping or adjudicating predictions; **read §I before declaring a
  contraction swept, an artifact provenance-verified, or a guard
  "fail-closed"**; §F is the one-screen re-read.

---

## A. Supersession & lineage (the most-repeated class)

**A1 — An acceptance decision must land in the accepted artifact's OWN durable
record, not only in the acceptor's documents.** Paid twice in one day-class:
one review (the ticket declared the corrected result set canonical in
`S4_VERDICT.md` and `state.json`, but the set's own `PROVENANCE.md` still said
"awaiting acceptance / predecessor is canonical", the slice note still pointed
at the predecessor, and the predecessor had no withdrawn marker — a reader
entering through either artifact was directed to the wrong canonical state);
same class as an earlier lineage single-valuedness finding. **Checklist when
declaring X canonical:** (1) X's own provenance records the dated acceptance;
(2) every active pointer (slice notes, verdict evidence lines) names X;
(3) the superseded set carries a LOCAL do-not-cite notice naming exactly what
is withdrawn; (4) a lineage grep shows zero unlabeled pointers.

**A2 — Producer lineage: a corrected artifact is produced end-to-end by the
CURRENT producer, never patched or reinterpreted.** In one review the analyzer was
refactored after the canonical run, so the shipped INPUT_MANIFEST bound a
pre-refactor hash — resolved only by a fresh canonical re-run with the current
analyzer. Another ticket applied the lesson correctly (full from-bags re-run, not an
npz patch) and rev2 still found the *narration* unsealed (A4).

**A3 — Superseded evidence stays on disk, marked, and is never overwritten.**
One ticket kept `s1_report.json` byte-identical, marked
SUPERSEDED-do-not-quote; another's `WITHDRAWN_COLUMNS.md` names the four corrupted
columns and states what remains valid. Corollary: result folders are
rev-suffixed (`_rev1`), and analyzers take an output-dir override so a re-run
*cannot* overwrite shipped evidence (`S4_OUT`). Suffix semantics:
the default suffix counts the ARTIFACT revision (`_rev1` = first revision);
if a file instead carries the number of the review round that forced it (for example
`WAVE3_SCORING_rev4.md`), its own header must say so — never mix the two
conventions silently in one ticket.

**A4 — "Re-run from the sources" is testimony until a manifest binds bytes.**
An input/output manifest must bind exact source identities/hashes, the
producer, and its outputs; a dirty worktree is recorded honestly as dirty
rather than bound as if clean (one ticket re-scoped its manifest
as an output-freeze because external bags were not hashed — say what is NOT
sealed).

**A5 — `blocking_open` is one truth.** Do not declare 0 while any durable
record contradicts the resolution (one review: numerically complete, lineage
contradictory ⇒ the 0 was premature); when items remain, keep the honest count
(one ticket kept 3 open). Correct a premature claim by amendment, not erasure.

**A6 — A recorded hash is a RECOVERY path: before writing "unrecoverable",
check whether anything the archive hash-binds still exists — and archive it
before it doesn't.** One response answered an unbound-configuration finding with
"there is nothing to recover — the evidence was never captured" and marked the
whole profile permanently UNVERIFIED; the next review found the two files whose sha256
all 11 provenance JSONs record still on disk, byte-identical, in a mutable
install tree that the next `colcon build` would overwrite (they decoded N=3, the
9/6 band, and the OLD σ profile). Two failures in one move: recoverable evidence
discarded, and the UNVERIFIED label over-broadened across a recoverable axis and
an unrecoverable one. **Rule:** enumerate what the provenance binds and test each
binding before declaring anything lost; copy surviving external bytes into the
ticket the moment you find them; then state the binding in **tiers** — never
witnessed / hash-bound *declared* but live value unwitnessed / stored label —
because collapsing the tiers is wrong in *both* directions.

## B. Review-round discipline

**B1 — Verify the reviewer — and verify your own verification instrument.**
In one response the reviewer's corrected numbers were exact, but my
spot-check first "refuted" their saturation values because I took the median
of a binary flag where the defined semantic was the mean (fraction). In another review
the reviewer's own counterexample was wrong (CRLB indefinite → actually
singular). Both directions fail; recompute with the *defined* semantics before
adjudicating either way.

**B2 — A review document can be stale against its own self-corrections.**
One review's remaining-work table still recommended the "G ≈ 0.81 tracking"
wording its own F4 self-correction had withdrawn; another review audited a
reviewer-overwritten response that was stale against the repo. Follow the
self-corrected body, and record the discrepancy in the response rather than
silently choosing.

**B3 — Never rewrite reviewed or produced records; append supersession.**
Stamps are append-only (`PREDICTIONS_STAMP.md` addenda); acceptance goes
into a provenance *addendum*, corrections into `revN_response.md` — the
audit trail must show what was believed when.

**B3a — Answer every finding on its own, with the fix shown at every place it occurs.**
A one-line "accepted, fixed" per finding let the same wording survive in two other places of a
deliverable while the response said it was fixed (the fifth recurrence of
one recorded lesson). `revN_response.md` therefore gives each finding of `revN.md` its own heading
naming the finding ID, with these fields: the reviewer's claim quoted; the verdict (accept,
partial, reject) with the reason and mistake class; every location where the problem occurs,
found by a search that is written out (`grep`, `rg`, a re-read section), not only the cited line;
the change at each location (before → after, or "none" only for a rejected finding); and the
re-check run on disk after the change. A code finding that is accepted also names the regression
test that failed before and passes after (or "none" with the reason). The same format serves
document reviews and code reviews. `tools/review_response/check_response.py <revN.md>
<revN_response.md>` checks it and `qrispy lint` runs it on an open ticket's latest response for
reviews registered from 2026-10-18; the template is `.claude/skills/qrispy/templates/rev_response.md`.

**B4 — An abstract-level grade is not a novelty lock.** One ticket's Lemma A
"novelty" survived two verifications and collapsed only on a full-text read
(Nardone & Aidala 1981 Eq. 19), two tickets later. Novelty and
prior-art-collision claims require the full text of the graded primaries.

**B5 — Prove-clean, not claim-clean.** The reviewable unit is the evidence
chain, not the sentence. A withdrawn or refuted item
is *recorded* (a review's own draft withdrawal of a finding is the model), never
silently deleted.

**B6 — Pin the sha256 of every artifact you quote at read time, and re-check it
before writing.** In one ticket rev1 read `S4_FINDINGS.md` at
14:11 and wrote at 15:47 — the file had been rewritten at 14:25 and again at
15:36 while the review was open, so rev1 charged the deliverable with an
*omission* ("candidates, none selected") when the on-disk text by then committed
a *wrong selection*. The finding survived only because the newer text was worse;
the quotation was stale either way. A review round and a correction round can be
open on the same file at once — same class as *"a glob over a mutable dir is a
selector, not a binding"*. Rule: record `sha256sum` beside every quoted
artifact when read; diff against it immediately before the review is written;
if it moved, re-read and say so in the review's evidence section (an
"as of `9ec99d0e`" line is the model).

## C. Instruments & analyzers

**C1 — Bind array/message layouts by schema, not by counting.** In one review
five off-by-one indices into `pn/diagnostics` shipped a saturation "fraction"
of 8.9 and a 500 g acceleration; the +1 `a_pn` slice produced *plausible*
numbers and was invisible. Physical-range asserts catch only the gross slips
(rev2 R2-F3) — bind the layout (field count + named offsets), add a synthetic
layout test that distinguishes adjacent blocks, and assert against configured
limits where they exist.

**C2 — Keep two independent measurement paths for load-bearing quantities.**
The index bug was caught precisely because the live covariate logger and
the bag analyzer measured the same quantities through different code; their
disagreement (a_meas ≈ 5222) was the alarm. When only one path exists, treat
its numbers as unaudited.

**C3 — Discard instruments with reasons established on CLEAN inputs, and keep
the discard recorded.** One ticket's xcorr-lag was discarded first for an incomplete
reason (its input was also corrupted — rev1 F2); the discard became durable
only after the clean-data result (non-causal lag in 27/32) matched another ticket's
independent rejection of whole-engagement xcorr. A wrongly-reasoned discard
invites a later session to resurrect a genuinely unsuitable instrument.

**C4 — Unit/ordering checks on scores, especially with ∞ or caps.** In one review
capping ∞-scores at 99 silently REVERSED the committed-∞ ordering and
flipped a verdict. Any score that mixes finite values with sentinels needs an
explicit ordering test.

**C5 — Faithfulness: verify equation direction/sign/regime against the source
before calling an implementation a reproduction; label adaptations.** One finding:
an equation's sign/direction (Eq. 89); one ticket's arms were proxies, not literature classes,
and were relabeled. "Adapted from" is honest; "faithful to" is a checkable
claim.

**C6 — Read the code/state-machine before asserting behavior.** Recurring
user-corrected class (memory: verify-before-asserting). Fresh examples: the
peer-ray "rate" was not a config flag anywhere (it was detection availability
× a 10 Hz tick); `yolo_result_vision` was a different message type
than its name suggests, and the wrong-typed subscriber received nothing while
*also* breaking bag recording.

## D. Claims & pre-registration

**D1 — Stamp before any run; re-scope BEFORE the run, in the stamp.** One ticket's
P2 was withdrawn at Q (two-point contrast cannot test dose–response) and
re-registered as conditional — recorded pre-run, so the null contrast did not
look like a post-hoc excuse. Baselines that recalibration may move are stated
as such in the stamp (Addendum 1 restated ② baselines before the GPU go).

**D2 — Adjudicate every stamped prediction, either way; refuted-as-worded is
a result.** One ticket's R-a ("gain debit shrinks every set" — it shrank none:
authority slack) and B3 ("GT velocity eliminates strands" — it did not: the
divergence lives in the position channel) each taught more than a supported
prediction would have.

**D3 — The first mechanism story is provisional until an instrument confirms
it; keep the refinement trail.** One slice went terminal-ε_v → early-transient →
tail-chase-starving-set in one day, each step driven by a sharper instrument
(covariate medians → fixed-offset ZEM → R(t) pass structure), with the
discarded intermediate instruments recorded (§C3). Another ticket's rate-not-range
correction and a third's mechanism-claim contraction are the same pattern: write
"mechanism = hypothesis" until the discriminating measurement exists.

**D4 — License claims to the tested regime; counterfactual instruments yield
conditional sentences.** The forced-ray arm licenses "*if* detection reached
25 Hz…", never "the deployed system works"; adopt the review-issued
claim-safe sentence as the citable form until the next gate.
Observation-layer/proxy results never become closed-loop
success claims without the matching closed-loop experiment (repo claim
discipline).

## E. Concurrency & identity

**E1 — Another session may be editing the same repo: check attribution before
flagging or reverting.** One review flagged a writing-plan edit that
belonged to a concurrent session (withdrawn by the user); another review's F1 was a
replay-vs-authorization conflict resolved by explicit user adjudication. Check
`git status`/state files and ask before treating a foreign edit as a finding.

**E2 — Ticket identity: numbers collide; prefix cross-repo references.**
Two tickets can share a number (a phase-map ticket and a dual-control ticket did); a number was reused after
a ticket's demotion (verified no external references first, and the
reuse is recorded in `state.json`). External stacks have their own colliding
numbers — always `<SYSTEM> ticket NNN` (QRISPY rule), and verify
which ticket a bare number means before acting.

---

## F. The one-screen repeat-offender list

1. Declaring canonical without updating the artifact's own record — run the
   A1 four-point checklist every time.
2. Trusting a re-run narration without a byte-binding manifest (A4).
3. `blocking_open = 0` while a durable record still contradicts it (A5).
4. Refuting a reviewer with a mis-specified check of your own (B1).
5. Following a review's stale table instead of its self-corrected body (B2).
6. Novelty claims from abstract-level grades (B4).
7. Counting array offsets by hand; one measurement path for a load-bearing
   number (C1, C2).
8. ∞/cap score orderings without an ordering test (C4).
9. "Faithful reproduction" without checking sign/direction/regime (C5).
10. Asserting behavior (rates, topics, types, state machines) without reading
    the code (C6).
11. Post-hoc re-scoping of predictions; unadjudicated stamps (D1, D2).
12. Shipping the first mechanism story (D3).
13. Unconditional sentences from counterfactual instruments (D4).
14. Treating a concurrent session's edit as your finding, or acting on a bare
    colliding ticket number (E1, E2).
15. Writing "unrecoverable" without testing what the archive's own hashes
    still bind (A6).

**Maintenance:** when a review round pays for a *new* recurring lesson, add it
to the matching section, record the ticket that paid in `HISTORY.md`, and bump `Last verified`.
One-off mistakes stay in their ticket's rev files; this file is only for the
classes that have recurred or plausibly will.

## G. Added 2026-07-28 (paid by one ticket's S6 audit)

**G1 — A design property claimed in ACs/stamps must be verified in the
implementing code before any run.** One ticket stamped, ran, and reported a
"paired-seed" campaign; the conductor's seed only shuffles trial order — no
per-trial seed reaches any stochastic component. Every downstream document
inherited the false property. Before stamping a design property (pairing,
seeding, counterbalancing, matched noise), read the code path that would have
to implement it (C6's rule applied to *experiment design*, not just behavior).

**G2 — A manifest must be DETACHED: never edit a bound file to announce the
manifest that hashes it.** One ticket's first seal hashed `PROVENANCE.md`, then
appended the seal announcement to it — self-invalidating the manifest (rev4
B4). Freeze bound text first; generate the manifest after; the manifest,
superseded manifests, and verifier outputs are unbound by construction; store
the verifier output.

**G3 — A scalar error/uncertainty ratio is not a calibration test.** One ticket read
ε_v (3-D norm) over σ_v = √(tr P/3) (per-axis RMS) as "honest ≤1 /
over-confident >1"; a calibrated Gaussian expects ≈√3. Calibration claims
need the right statistic (NEES/coverage with declared dof) on a
freshness-contracted stream — otherwise report descriptively and write
"calibration untested".

(F-list additions: 16. verify the code implements the stamped design property;
17. manifests are detached, bound text frozen first; 18. no calibration
language without a calibration statistic.)

## H. Added 2026-07-28 (paid by one falsification-gate slice)

Two classes, each paid **three times in one slice**. Both produce the same
symptom — a criterion that reports GREEN or a null that reports RED — while the
mechanism under test was never exercised at all.

**H1 — A criterion can be satisfied (or violated) for a reason unrelated to the
mechanism it names. Always pair it with a degenerate alternative.** Three
instances in one slice:
- gate 4a ("v2 must refuse under honest ε_v ∈ [0.9,1.5]") reported 0/12 refusals
  — but a 2×3 factorial showed **ε_p alone blocked every commit** (z·σ_p = 0.64 m
  > r_kill = 0.5 m) *before ε_v was consulted*; at ε_p = 0.05 a large ε_v still
  permitted commits. The green demonstrated nothing about ε_v.
- criterion B1 ("must not commit immediately") was **satisfiable by never
  committing**, and that is exactly how it "held" in the first run.
- criterion B2 ("commit in a starved geometry") used `vf = 1.0`, a **slow
  target** rather than a constant-bearing starved geometry, so it tested the
  wrong regime.

  **Guard that caught all three:** evaluate the criterion against a *degenerate
  alternative* (a factorial over the confound; "never/always" controls; a
  competing rule) and require the criterion to *distinguish* them. A criterion
  that cannot separate the mechanism from its confound is not evidence. This is
  §D2's "adjudicate either way" applied to the *criterion* rather than the
  prediction, and §B1's "verify your own instrument" applied to *acceptance
  tests*.

**H2 — Before interpreting a result, assert the quantity under test is LIVE and
VARIES.** Three instances, all producing confident-looking numbers from a
mechanism that never ran:
- a test harness monkey-patched the *source module's* class, but the driver had
  bound that name into **its own namespace** at import — so both arms ran the
  same rule. The tell was that the two arms' decisions were identical
  element-for-element.
- the "information rate" fed to the rule was `_last_fkappa`, which in belief
  mode is the clamped **lexicographic score**, not $F_\kappa$ — a constant 0, so
  the rule silently degenerated to its base condition.
- the twin never called the planner's `step()`, so the CEM never ran, the
  information statistic was never populated, and a "no information yet" guard
  blocked **every** commit — a 0/12 that was pure harness artifact.

  **Guard:** a one-line pre-flight that prints the statistic under test before
  the run (`is it non-zero? does it change with the input it is supposed to
  depend on?`). Exact-tie or all-identical outputs across arms that *should*
  differ are the alarm (§C2's two-path logic applied to *arms of one
  experiment*). Corollary: **a null result is not reportable until the
  instrument is shown live** — two of these were nearly written up as findings.

**H3 — A stamped risk left untested is an open risk, not a passed one.** The
S4-B stamp pre-registered "threshold smuggling" (the stopping rule merely
relocating the absolute threshold). It was measured only in a *broken*
configuration (flat 0/12, uninformative) and not re-run after the fixes; when
finally re-run on the valid configuration it was **confirmed** (commits 6/12 →
11/12 as `stop_frac` 0.001 → 0.8). Re-run every stamped risk on the
configuration the verdict is based on, and say which risks remain untested.

(F-list additions: 19. criteria that cannot separate mechanism from confound —
pair with a degenerate alternative; 20. interpreting results before asserting
the tested quantity is live and varying; 21. stamped risks measured only on a
superseded configuration.)

**G4 — A claim contraction is a SWEEP, not an edit: enumerate the document set
first, then grep-verify zero unmarked residues.** One ticket paid three review rounds
(rev2, rev5, rev6) for the same class: each correction pass fixed the documents
the responder remembered and missed others (the canonical set's own provenance;
a consumer ticket's handoff; state ownership fields; a verdict's earlier
sections; a slice's closing quote). Before answering any contraction-type
finding: list EVERY active document (state fields included, consumer-ticket
copies included), patch or supersession-mark each, then grep for the withdrawn
phrases and require zero unmarked hits. (F-list addition: 22. contraction =
enumerated sweep + zero-residue grep.) **Extended by §I1 — the grep half of
this rule cannot certify; see below.**

## I. Added 2026-08-02 (paid by one five-round contraction)

Three classes, one root. Five review rounds each closed a real defect and each
declared the job done; the next round found the same failure one layer deeper.
In every case the *correction* was sound and the **coverage of the check that
blessed it was implicit** — so a green read as total.

**I1 — A negative sweep (grep for known-bad strings) can catch REGRESSIONS; it
cannot CERTIFY a contraction. Enumerate positively.** §G4 fixed the
document-list half of the sweep and left the pattern-list half open. One ticket
paid four consecutive rounds for it:

- rev2 caught rev1 on the **document list** (three headline files patched, ~10
  left unmarked);
- rev3 caught rev2 on **inflection** — the recorded pattern `"AC-1b PASSES"`
  structurally could not match `AC-1b passed`, which survived in the deliverable;
- rev4 swept with its own inflection-tolerant patterns and reported zero hits;
- rev5 found two more with a fourth pattern set (`"conservative upper
  diagnostic"` unmarked in `ticket.md`'s hypothesis section; `"R4 is answered"`
  unenumerated in a slice banner) — and the acceptance criterion that rev4 had
  just recorded as MET regressed to NOT MET.

The oracle is the pattern list, and the pattern list is written by whoever did
the fixing — so it encodes their memory of what they changed, not the space of
what could be wrong. Paraphrase is unbounded; a string oracle never closes.

**Guard (four steps, in order):**

1. **Positive enumeration, once.** List every *claim-bearing sentence* in the
   active set (`file:line`), tag each with the object/scope it speaks about and
   its licence status, and ship the enumeration itself as the evidence artifact.
   "N sentences, each with a verdict" is checkable; "zero grep hits" is not.
2. **Invert the grep into a recall net.** Search for claim-indicator vocabulary
   (`equals, preserves, bounds, exact, conservative, upper-bounds, cannot, must,
   proves, implies, answered, gap`) to surface *candidates for triage* — high
   recall over "language that makes a claim", not high precision over "phrasings
   I remember writing".
3. **Make it syntactic.** Where a ticket distinguishes two objects/scopes that
   are easy to conflate, require every claim sentence to carry an explicit tag
   (`[object-A]`, `[object-B — deferred]`). The rule then becomes mechanical:
   *an untagged claim sentence is a finding.* This is the only form a grep can
   actually certify, because it converts an unbounded semantic check into a
   bounded syntactic one.
4. **Later rounds diff, don't re-sweep.** Re-check only the sentences that
   changed against the stored enumeration, instead of inventing a new pattern
   set each round.

**I2 — Verify the BOUND SET, not a subset of it — and verify the STORED
artifact, not a recomputation of it.** One ticket's manifest bound **14** hashes
(producer, imported dependency, output report, and 11 preserved superseded
artifacts); its `--expect-manifest` verifier checked **3** — and the third
compared a *freshly recomputed* report against the manifest without ever opening
the stored report file. Demonstrated at rev5 on scratch copies:

- editing the **stored** report's headline number (D2 worst ratio
  `0.9513 → 0.1234`, a figure quoted in the deliverable, the closeout, the claim
  licensing and four review conclusions) left the documented drift check
  returning **exit 0 `[PASS]`**;
- editing a **preserved** artifact went undetected *and* the documented
  reproduction command silently **re-baselined that binding to the tampered
  hash** — the laundering path a prior round had closed for the three checked
  bindings was still open for the other eleven.

Two different questions hide inside one command: *"would a fresh run reproduce
the manifest?"* and *"is the file on disk the one the manifest binds?"* Only the
first was answered; only the second protects a citation.

**Guard:** the verifier's checked set must **equal** the manifest's bound set —
enumerate the bindings and check each. Hash files **as stored**; a recomputation
is a separate (also useful) check and must be reported separately. Never
re-derive a binding as a side effect of a normal write: on mismatch, refuse with
a distinct non-zero exit and require an explicit `--write`/`--force` to
re-baseline. This is the next lesson in the §A4/§G2 line — a manifest is only as
strong as the subset its verifier actually reads.

**I3 — An audit that does not state its own coverage is a narration.
"Verified" is not a verdict; "verified X, NOT Y" is.** I1 and I2 stayed
invisible for rounds for the same reason: neither artifact said what it did
*not* cover. One drift-check record asserted the guard "binds what the
manifest binds — the producer, the imported dependency, and the output report"
while the code checked 3 of 14 bindings and opened no file; three further
durable records inherited the overstatement ("read-only fail-closed",
unqualified).

**Guard:** every verification artifact carries an explicit **covers / does not
cover** section in checkable terms (which files, which properties, which axes),
and every downstream sentence citing it inherits that qualification. When a
guard is called *fail-closed*, name the axes it closes and exercise **each** on
its negative branch — §H2 applied to a guard's *scope*, not just its liveness:
rev2's check was exercised only on the clean branch, rev3's on three axes, and
the fourth axis was the one that failed at rev5.

**I4 — A verdict a rule can compute is not an adjudication, and a checker that
tests `generated ⊆ shipped` is not symmetric.** One ticket replaced its grep sweep
with a positive enumeration (I1) and then made the enumeration reproducible by
generating it (rev7). rev8 showed what that had cost: the tag/verdict columns
were regex output while the artifact called them "hand-adjudicated", and the
rule certified an injected sentence — *"the closed-loop policy-Jacobian gap is
provably negligible for AC-2, so feedback cannot starve the estimator"*, the
single most clearly forbidden sentence in the ticket — as **"deferral stated
correctly"**. It could not do otherwise: the tokens it keys on (`pcrlb`,
`ac-2`, `unlicensed`, `unknown`) appear in a correct deferral and an unlicensed
assertion alike. That similarity is *why* the class is hard, and it is what
five rounds of grep had already failed on. Separately the checker compared only
whether every generated row appeared in the artifact, so a **fabricated row
pasted into the artifact passed at exit 0** — I2's subset defect, recurring in
the tool built to retire it.

The deeper failure is a **correction applied only at its discovery site**. The
same superseded phrase ("conservative diagnostics") sat in four records; the fix
had reached one file and its banners, and three survivors went unseen for three
rounds — **all of them in rows the rule had bucketed "not a claim"**. A bucket
no human has read is not a finding-free bucket.

**Guard:** store adjudicated verdicts as **data keyed to the exact line text**,
and have the generator emit `UNADJUDICATED` (and fail) for any row without one —
so a sentence nobody read cannot be certified, and editing an adjudicated line
drops its verdict and forces re-adjudication. Compare generated regions
**byte-for-byte in both directions**, delimited by explicit markers, so an extra
row fails exactly like a missing one. Bind the artifact to the judging tool's
**self-hash** (§G2), and record the negative branches with their exact mutations.
State plainly which verdicts *differ* from the rule and which merely *concur*
with it after reading — concurrence is a judgement, not an independent
derivation. And when a phrase is superseded, sweep the phrase **class** across
the record (§G4), not the sentence you happened to find.

(F-list additions: 23. certifying a contraction with a negative grep sweep;
24. a verifier that checks a subset of the manifest's bindings, or a
recomputation in place of the stored artifact; 25. "verified" with no coverage
statement — and fail-closed guards exercised on only some of their axes;
26. a rule-computed verdict presented as an adjudication, and a one-directional
`generated ⊆ shipped` check; 27. a correction applied at its discovery site and
never swept across the record as a phrase class.)

**Numbering note (2026-08-03).** The §F body list still ends at 15; items 16–27
above were proposed by §G/§H/§G4/§I and never merged into it. Before this fix two
numbers were claimed twice — 15 (§F's A6 entry vs §G's first addition) and 18 (§H's
first addition vs §G4's). The additions are now a single consistent 16–27 sequence.
Merging them into the §F body is still outstanding.

## J. Added 2026-08-09 (paid by one ticket's five review rounds — six recurrences of one failure)

That ticket ran five review rounds, 19 blocking findings. **Six of them were the same
failure**: a correction that landed in one place and not another. §I's lesson —
a green read as total because the check's coverage was implicit — is the same
root, and it was paid again at the *prose* layer rather than the sweep layer.

**J1 — A correction must DELETE what it corrects, and the test must assert
ABSENCE.** A `.msg` header asserted "an honest UPPER BOUND" twenty lines
above the field note retracting it, and the doc test written to prevent exactly
that asserted the *presence of the correction* and passed. A presence-assertion
cannot see a contradiction sitting above the string it looks for. Ban the
retracted sentence; do not append a qualification beneath it.

**J2 — The SCOPE of an absence check is the part that has to be argued, not the
list of phrases.** The ticket built a standing 8-phrase × 8-file check at rev2 for
exactly this failure, and rev3 found the fifth recurrence in files the check did
not cover — its scope had been drawn around the files rev2 happened to be
reading. Two further defeats surfaced when it was extended: a `glob(...)`
filtered through `is_file()` could scan **zero files and pass** (§F's "a check
that cannot fail"), and a raw substring match missed a sentence markdown had
**wrapped across a line break**. A scan needs an explicit file list, an asserted
file count, whitespace normalisation, and a positive control proving it is not
vacuous — the ticket claimed that control in its record for a whole round before
anyone checked that it existed.

**J3 — A phrase ban catches copies, never rewords.** The sixth recurrence sat
*inside* the extended scope: a node docstring restating a retracted claim in
different words. When a file has hosted three recurrences, the remedy is to
**shorten what it asserts in prose**, not to lengthen the ban list. State this
limit in the test itself, so a green run reads as "no retracted sentence
survived verbatim" rather than "the record is consistent".

**J4 — A claim whose computation is not in the artifact is the same defect as a
claim whose retraction landed in one file.** Both are asserted-not-checked and
both survive until someone re-derives them. The ticket asserted a residual statistic
from a scratch run that never entered the repository; the cited script had the
relevant function *defined and never called*, and the number a reader would find
in its JSON belonged to a different quantity. Worse, the statistic cited (a
median) was not the one the finding was about (a tail). **Compute it in the
artifact, and check that the statistic answers the question asked.**

**J5 — When a search has more degrees of freedom than the data has resolution,
its positive results are worth nothing and only its negative result is
evidence.** The ticket tested ~1700 (pairing-offset, sensor-sample) hypotheses per tick
to identify a covariance pairing; several offsets matched to machine precision on
most ticks, so "the assumed offset is consistent" carried no weight. Report the
denominator and the median size of the consistent set, and draw only the negative
conclusion — the quantity is unidentifiable from this data.

**J6 — Report the unexplained fraction FIRST, with its denominator.** The ticket drew a
verdict ("not falsified") over the 74 % of ticks its instrument could reproduce,
while a quarter to a third were unexplained by every hypothesis tested. A verdict
computed on the complement of an unexplained set is a statement about that
complement, and must say so.

---

## K. Added 2026-08-11 (paid by one ticket's five diagnostic boots — four wave-corrupting defects in three days)

**K1 — A green test is evidence only if you have seen it go red.** Every gate this
ticket added was run against a **`/tmp` copy of the pre-fix node**, and one of them
would have shipped useless: the arrival-axis carry-over test passed on the defect
until it was pointed at a copy that still had it. Restore by `rm -rf` + re-copy from
the repository, never by git (repo CLAUDE.md). A test written *after* the fix agrees
with the fix by construction; only the negative control says it detects anything.

**K2 — A test whose timing is EXACT can satisfy a boundary condition that no real
timing satisfies.** The `converge` settling-window test stepped a fake clock by
exactly 50 ms, deliberately, to keep a timing assertion off scheduler luck. That put
a sample exactly on the window's cutoff on every tick — the single timing an
off-by-one boundary admits — so the test passed and the mode silently degraded in
flight. **Making the test deterministic is right; making it aligned is not.** Jitter
anything a window, cutoff or tolerance comparison depends on, with a fixed
non-random sequence so the run is still reproducible.

**K3 — Verify after EACH fix, not once at the end.** Fixing one defect is what makes
the next one visible. The arrival-axis carry-over was invisible while the
reference was collapsed onto the initial LOS, and the settling-window off-by-one was
invisible while the axis never rebuilt at all. Two of the four defects were only
reachable in that order. Five short boots, ~35 min of GPU, against a 342-trial wave.

**K4 — A gate that re-types a value it could import will assert the wrong thing the
moment the value changes.** One ticket's item-10 checker hard-codes the expected arm
configuration; a later ticket redefined that arm twice in one night, and the checker would
have gone on passing against an arm nobody was flying. Its wave-2 replacement
imports the registered dict and checks the whole chain — prereg → generator →
manifest → archive — which a hand-copy cannot do. Applies to runbooks as much as to
code: a runbook names the one file that owns each value.

**K5 — A checker that is wrong in the SAFE direction is still wrong.** The
chain-vs-`SWAPS` check first counted literal occurrences of a script name and
reported a missing A9 relaunch on a chain that performs it through a shell variable.
A false alarm is not free: it is the reason gates get skipped on the run where they
are right.

## L. Added 2026-08-20 (paid by one ticket's rev1→rev3 — a false green that crossed a repo)

**L1 — An exclusion must be tested against the ACTUAL selector, and its control must be
shown to go red.** One ticket quarantined invalid bags by SUFFIX rename, then "confirmed"
the quarantine by re-running the QA and observing identical output. The QA's glob ends
in a trailing wildcard, so the rename excluded nothing, the re-run read the same
invalid bags, and the identity was guaranteed by construction — a §K1 recurrence in
records form. The invalid number (a realized target speed) had already propagated into
ANOTHER repository's design arithmetic before rev2 caught it. The discipline: (i) name
the selector that must not see the artifact and test the exclusion against IT (run the
glob); (ii) the confirmation run must be a control that CAN fail — state "pre- and
post-exclusion outputs must differ; if they do not, the exclusion did not work";
(iii) retain the consumer's own provenance (stderr, opened-file lines) in the archived
re-run, so the artifact settles which inputs were read.

**L2 — Corrections must land across the CLASS, not at the discovery site — and the
enumeration that enforces this needs an explicit scope.** Three consecutive rounds
had a fixed number survive somewhere the finding didn't point: slice note fixed /
state.json stale; a slice's own numbers fixed / the one number IMPORTED from another
ticket unchecked (and it traced to a self-declared provisional artifact); the withdrawn
premise's input replaced / its downstream outputs (ε, a table) left standing
unbannered. Remedy that worked: a claims→artifact enumeration with a stated
covers/does-not-cover line (state fields, consumer-ticket copies, cross-ticket imports
IN) — then later rounds diff against it instead of re-sweeping.
**Residual failure mode (added same day, paid by the next round's R4-B1 — the counter's own
first outing missed two survivors):** a number-anchored enumeration is blind to (a) a
correctly-bound number whose SOURCE STATUS is wrong (bound to a provisional artifact,
quoted as if registered) and (b) a RETIRED STATEMENT that contains no number at all
("quarantined by rename"). Anchor rows on VALUES (the defective wording is what needs
finding — a key phrase from the corrected text matches only itself), and keep a
retired-statements list beside the claims table, swept by phrase.

## M. Added 2026-08-29 (paid by one labelling defect surviving its own correction round)

**M1 — A finding names a defect CLASS, not a file.** One review ruled a
labelling pattern blocking (a "realized" axis whose labels were a hard-coded
cross-arm pooled median) and the correction pass fixed exactly the one file the
finding named (`report_obs_071.py`). The identical pattern — the same hard-coded
dict, the same word "Realized" on the axis — survived in `plot_boundary_071.py`
and its rendered figure, the artifact *most likely to reach a reader*, and
cost a blocking finding in the next round (rev_ac7_1 F-2). The discipline: when a
round rules a pattern blocking, the correction pass greps the ticket for the
pattern (the literal dict, the label string, the operator) and corrects **every
artifact that carries it** in the same pass — the report *and* the figure, the
generator *and* its output paths, the prose *and* the caption. A corrections map
that lists only the files the findings named is a checklist, not a correction.
Corollary (same round, A-1): after a rename-to-`_rev` correction, re-point every
generator and runbook line that still writes the superseded path, or a faithful
reproduction run mechanically re-commits the violation the round just fixed.
