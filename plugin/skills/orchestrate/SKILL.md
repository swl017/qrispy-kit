---
name: orchestrate
description: Run several child tickets of one parent ticket at once — split the parent, open the children, start a worker per child, supervise them, and integrate their results. Use when a ticket's plan has two or more parts that should run in parallel, or when the user asks to orchestrate, delegate or run tickets side by side.
when_to_use: '상위 티켓, 하위 티켓, 오케스트레이션, "나눠서 동시에", "병렬로 진행", "작업자 띄워", "하위 티켓으로 나누자", orchestrate, delegate, run in parallel.'
---

# Orchestrating child tickets

Definitions are in `${CLAUDE_PLUGIN_ROOT}/method/QRISPY_METHOD.md` §Orchestration; this skill is the procedure. You are the orchestrator only for the parent ticket you own (`state.json.session` is you). There is no standing orchestrator. A single child, or children run one after another, need none of this: do them yourself.

## 1. Split the parent

1. Write the children into the parent's `p_plan.md`: one row per child with its scope, the parent ACs it serves, what it needs from other children (`deps`), whether it changes code another child also changes, and whether it uses the GPU.
2. Splitting is a design decision of the parent: ask the user (a Q item in the parent's `q_questions.md`, or a `qrispy:plan-page` round when there are several) before opening any child.
3. Open each child with the `qrispy:ticket` skill. In its `state.json` write `"parent": "<SYSTEM NNN>"` (only the child names the parent); in its `ticket.md` say which parent ACs it serves. `qrispy show <parent>` and `qrispy ls --tree` must then list it.

## 2. Choose how each worker runs

| The work | Claude | Codex, Gemini |
|---|---|---|
| Short and bounded, its result is one document (research, a test, a review, a unit of code) | `qrispy worker headless --agent claude --job <child>/jobs/<id> …` | `qrispy worker headless --agent codex` or `gemini` |
| Long, or the user may want to step in (implementation, design) | `qrispy worker claude-bg --ticket "<SYSTEM NNN>" …`; the user joins with `claude attach <name>` | `qrispy worker tmux --agent codex` or `gemini`; the user joins with `tmux attach -t agents` |
| Changes code another worker changes at the same time | add `--worktree` (Claude) or start it in a worktree made by `${CLAUDE_PLUGIN_ROOT}/method/QRISPY_METHOD.md` §Worktrees | start it in such a worktree (`--cwd`) |

Headless fits only work that needs no permission dialog (reading files, searching, writing its answer): a call outside the allowed list (for example Python reading bags) is refused silently. Work that will need such calls goes to a Claude background session, where the user can answer the dialog.

`qrispy worker` is the kit's worker tool. Build the first prompt with `qrispy worker prompt --ticket … --parent … --parent-session <you> --agent … --task "<what to do, in two or three sentences>" > <file>`; it tells the worker to read the `qrispy:ticket` skill and its ticket, to write its own session name, how to report, and what it must not do. One interactive worker per child. Never pass a flag that widens permissions.

Before you start a worker that uses the GPU: `qrispy lock status` must be free or yours, and the run must sit inside a scoped go (§4). Tell the user the local start time of every worker you start.

## 3. Supervise

- Claude background workers: their status lines arrive as messages. Also run `qrispy worker watch --names <w1>,<w2> --heartbeat 300` as a background command, and start it again after every wake: it exits when a worker waits at a permission dialog (tell the user at once, with `claude attach <name>`), finishes its turn, or is gone, and every five minutes otherwise. `SendMessage(notify_when_idle=true)` alone is not enough: a worker stopped at a dialog is not idle, so it never fires.
- Headless runs and other agents: start `qrispy job wait <job dir> --heartbeat 300` as a background command; at each wake read `qrispy worker status`, the job's `qrispy job status` (a headless Claude run logs stream-json, so a growing `job.log` means it works), and the child's `jobs/worker/status.log`. When a headless run ends, read it with `qrispy worker result <job dir>`: it prints the answer and a `WARN` list of tool calls that were refused. A headless run has no dialog, so a refusal is silent and the worker may have narrowed its task; tell the user what was refused before you file the answer.
- `waitingFor: permission prompt` (`qrispy worker status` or `qrispy show`) means the worker is stuck at a dialog only the user can answer: tell the user at once, with the worker name and `claude attach <name>`.
- A worker that moved itself into a git worktree (`git worktree list` shows a branch you did not start it on) has left its ticket files stale on main: stop it at the next turn and ask the user how to bring the ticket files back. Ticket files live only in the main checkout; a worktree is for code.
- Signs of life of a busy Claude worker are in `qrispy worker status` and in each `watch` heartbeat line: the age of its transcript file and the spinner's output-token count. A long generation (a big Write) moves the tokens while the transcript stands still; a hang moves neither.
- A worker silent for two heartbeats while alive (neither its files, its transcript nor its token count moved): read its output (`claude logs <name>`, the tmux pane, `job.log`) and tell the user. Never restart a worker on your own; a false "dead" makes a duplicate worker.
- Before you ask a worker to do anything, re-read its ticket's `state.json` and `q_questions.md`: the files win over your memory and over messages.
- Send to a session's name now, not the name you remember: `qrispy show <ticket>` resolves the recorded `session_id` to the current name (`old → now new`). When you reopen as the parent, run `qrispy worker whoami`, update the parent's `session` and `session_id`, and tell each worker your new name in one line.

## 4. GPU runs and scoped go

A run on the GPU (sim or training) needs the user's go, every time, unless the user gave a scoped go as a Q item: what (recipe, experiment), max hours, max runs, output path, until (date). Record it in that ticket's `state.json.go_scopes` (`[{"q": "Q-7", "kind": "sim", "what": "…", "max_hours": 6, "max_runs": 8, "out": "…", "until": "YYYY-MM-DD"}]`). `qrispy show <ticket>` prints each scope with the hours and runs already used (from the jobs launched with `qrispy job run --go "<ticket> Q-n"`). Start a run only when it fits what is left; otherwise ask. Say which scope a run uses when you report it.

## 5. Decisions

The user may answer in any session. Whoever receives a decision writes it verbatim into the `q_questions.md` of the ticket it belongs to (or sends it to that ticket's live session), and, when that ticket has a parent with a live session, sends the parent one line: `<ticket> decision: Q-n = <gist>`. Siblings align technical details (an interface, a file format, a shared definition) by messaging each other directly and send you a one-line copy (`<ticket> aligned with <sibling>: <gist>`); anything that changes another child's scope or ACs, or needs the user, comes to you. When the children owe the user decisions, do not pass them on one by one: gather every unanswered Q item of the parent and its children with `qrispy questions --tree <parent> --html <parent dir>/lavish/questions_<MMDD-HHMM>.html` and open that one page with the `qrispy:plan-page` skill. Record each answer verbatim in the ticket its card names, and tell that child's worker. Questions answered later reappear on the next page. Never take a user's answer from a worker's terminal (`claude logs`, a tmux pane): the input box shows Claude Code's suggested replies in dim text, and once escape codes are stripped a suggestion looks like submitted input. The evidence of a decision is the ticket's `q_questions.md` or a `decision` line from the worker.

## 6. When the user is away

When the user says they are leaving (or gives a time), run `qrispy worker away on [--until HH:MM]` and send every running worker the notice it prints (finish the current step, then stop; no questions or notices to the user; no GPU run). While away, `watch` and `qrispy job wait` do not wake you on heartbeats, dialogs or ended jobs; they keep events for later, and `qrispy lock take` refuses new GPU runs. Send the user nothing. When they are back (they say so, or the `--until` time passes and `watch` wakes you), run `qrispy worker away off`, send every worker the back notice, and give the user one summary: what finished, what waits on them, and the decisions page from `qrispy questions`.

## 7. Integrate and close

When a child closes, read its `z_closeout.md` and `CITE.md` (never its working files) and update the parent's AC table and slice note. Stop and remove finished Claude workers (`claude stop <name>`, `claude rm <name>`) and close finished tmux windows. A parent closes only when every child is closed or superseded (`qrispy lint` warns otherwise).

## What you must not do

- Decide research questions for the user (claims, experiment design choices, review waivers, which result to adopt).
- Start a GPU or sim run outside a scoped go, or take over a GPU lock another ticket holds.
- Commit on main (workers may commit on their own `wt/*` branch); merging into main needs the user.
- Edit a child's files yourself; message its worker instead.
- Ask a worker to do what your own permissions block.
