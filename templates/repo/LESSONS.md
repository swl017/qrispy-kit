# LESSONS — ledger of agent mistakes

The one incident ledger of this repository. Definitions, classes and the promotion rule are in the kit's `method/QRISPY_METHOD.md` §Lessons; this header only summarises them.

- **Mistake**: an agent action that contradicted a written rule, the user's explicit intent, or the actual state of the repository, and cost user time or evidence. A negative result, a refuted hypothesis or a recorded change of requirement is not a mistake.
- **Classes**: `rule-violation` (a written rule was broken), `missing-knowledge` (the needed rule or fact was nowhere), `unrecorded-drift` (work left the intent without a record), `record-mismatch` (a record disagrees with reality: a false green, a stale state, a wrongly copied number).
- **Duty**: the agent writes an entry in the same turn, unasked, when the user corrects it, when a review finds a defect of its own making, or when a guard hook blocks it.
- **Promotion**: a lesson first goes to the layer loaded when that work happens (a skill or a recipe). A written rule broken twice becomes a mechanism (a hook, a check script, a required template field); then shorten the sentence. Another warning sentence is not a promotion.
- **Failure classes**: recurring classes are explained in the kit's `method/DEV_REVIEW_RECIPE.md`; link an entry to its section when one fits.

Format: `## L-NNN · date · ticket · class · how it was found`, then what / cause / fix / recur.

---
