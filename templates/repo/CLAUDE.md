# Repository Instructions

<One paragraph: what this repository is for.>

## How work is done

- Work is organised as QRISPY tickets under `{root}/` (system `{system}`; `qrispy.json`). The `qrispy` Claude Code plugin carries the method, the skills and the guard; repository-specific rules are in `{root}/METHOD_LOCAL.md`.
- Agents other than Claude Code (Codex and others read this file as `AGENTS.md`) do not get the plugin's session-start rules: run `qrispy rules` first and follow them, and use `qrispy` for ticket state, jobs and the GPU lock.
- Agent mistakes go to `{root}/LESSONS.md` in the same turn, unasked.
