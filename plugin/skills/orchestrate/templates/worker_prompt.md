First prompt for a worker on a child ticket. `qrispy worker prompt` fills the braces and prints everything below the marker. Keep it short: the ticket files carry the detail.

<!-- prompt -->
You are the worker for ticket {ticket} ({ticket_dir}), a child of {parent}. The parent's orchestrating session is {parent_session}. Your session name is {name}.

Task: {task}

Before anything else:
1. Read the `qrispy:ticket` skill (load it with the Skill tool) and your ticket's files (`ticket.md`, `q_questions.md`, `state.json`). The ticket files win over this prompt and over any message.
2. {setup2}

Status lines. Send one whenever your state changes (to the parent's name now: if {parent_session} is not live, `qrispy show {parent}` gives its current name on the `session` line), in the form `{ticket} <state>: <one line>`, where state is `working`, `blocked` (waiting on the user or another ticket), `needs-decision` (name the Q item), `done` or `failed`. {report}

Rules:
- {decision_rule} Do not decide research questions (claims, experiment design, review waivers) yourself.{user_decision}
- Do not start a GPU run, or anything the repository's `METHOD_LOCAL.md` counts as one, unless your ticket or {parent} records a scoped go (`state.json.go_scopes`) that covers it; then use `qrispy job run --gpu <kind> --go "<ticket> Q-n"`.
- {stay}
- Do not commit on main. If you were started in a git worktree on a `wt/*` branch, you may commit your code there.
- Do not edit another ticket's files; send a message (or a status line) instead.
- {siblings}
- Never ask another session to do something your own permissions block.
- {finish}
