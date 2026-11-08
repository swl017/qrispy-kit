# qrispy-kit

QRISPY is a ticket workflow for research and implementation work with coding agents: each task is a ticket folder holding its questions, design, plan, slice notes, independent review rounds and closeout. This kit carries the workflow as a Claude Code plugin (`qrispy`) plus one command (`qrispy`), so that a repository needs only its own ticket folders and a small `qrispy.json`.

It was extracted from the repository of the RAL paper on active cooperative sensing (RAL ticket 090); `plugin/method/HISTORY.md` records which ticket each rule came from.

## What is in it

| Part | Where | What it does |
|---|---|---|
| method | `plugin/method/` | `QRISPY_METHOD.md` (every ticket file and field), `REVIEW_PROMPT.md` (the reviewer's contract), `DEV_REVIEW_RECIPE.md` (recurring failure classes), `HISTORY.md` |
| skills | `plugin/skills/` | `qrispy:ticket` (open, continue, close a ticket), `qrispy:review` (a review round), `qrispy:cite` (quote a ticket's result), `qrispy:orchestrate` (child tickets in parallel), `qrispy:plan-page` (decision pages; needs Lavish) |
| reviewer | `plugin/agents/reviewer.md` | the read-only review subagent, `subagent_type: qrispy:reviewer` |
| hooks | `plugin/hooks/` | the core rules (`plugin/rules/CORE.md`) put into every session of a repository that uses the kit; and `guard_git.py`, which blocks destructive git commands (`checkout`, `restore`, `reset`, `clean`, `stash`) and asks before commits, registered by `install.py` for every repository on the computer |
| command | `plugin/bin/qrispy` | `qrispy ls|show|inbox|lint|…`, `qrispy job run|wait|status|handled`, `qrispy review …`, `qrispy worker …`, `qrispy lock …` (the machine's GPU lock), `qrispy init`, `qrispy rules`; `qrispy help` lists them |
| repository skeleton | `templates/repo/` | what `qrispy init` writes |

## Install on a computer (once)

Needs `git`, `python3` (3.8 or later) and the `claude` CLI on the login shell's PATH.

```bash
git clone git@github.com:swl017/qrispy-kit.git ~/Code/qrispy-kit     # any folder; it is read in place
python3 ~/Code/qrispy-kit/install.py             # check only: shows what is missing
python3 ~/Code/qrispy-kit/install.py --install   # register the clone as a local marketplace and install the plugin,
                                                 # register the guard and the deny rules, link ~/.local/bin/qrispy
```

Scopes follow the usual split: what protects every repository is set for the user, the workflow only where a repository asks for it. The guard hook (`python3 -I "<clone>/plugin/hooks/guard_git.py"`) and the deny rules go into `~/.claude/settings.json` and hold in every repository. The plugin is installed but turned off for the user; a repository turns it on in its own `.claude/settings.json` (`qrispy init` writes that line), so its skills and rules appear only there (checked by experiment; the record is in the RAL repository, ticket 090, `evidence/plugin_spike/r8_project_scope.txt`). `--install` backs up `~/.claude/settings.json` before changing it, and replaces an older registration of the guard (for example a copy in `~/.claude/hooks/`, which is kept as `.retired-<time>`). If the clone moves, run `install.py --install` again: the guard is registered by its path.

**Updating**: `git pull` in the clone, then start a new session (an open session can run `/reload-plugins`). Claude Code reads a plugin installed from a local marketplace from the clone itself; it also keeps a copy under `~/.claude/plugins/cache/`, which it does not use (checked by experiment; the record is in the RAL repository, ticket 090, `y_slice_1.md` §2a).

## Set up a repository

```bash
cd <repository root>
qrispy init --system ABC [--root tickets]
```

It writes `qrispy.json`, `<root>/LESSONS.md`, `<root>/METHOD_LOCAL.md` (the repository's own rules, which may narrow but not loosen the kit's), a `CLAUDE.md` skeleton and `AGENTS.md` (a symlink to it) when they are missing, and merges into `.claude/settings.json`: the plugin enabled, the deny rules, read-only `qrispy` commands allowed. It never overwrites a file. Then check with `qrispy lint --repo`.

## Other agents

Codex and other agents read `AGENTS.md` (the same text as `CLAUDE.md`). They do not load Claude Code plugins, so they get neither the skills nor the guard hook nor the session-start rules: the `CLAUDE.md` skeleton tells them to run `qrispy rules` first, and the `qrispy` command works the same for them. Their own approval settings must stand in for the guard.

## Conventions for the kit's own text

Help and usage text (`qrispy … --help`, the usage lines a command prints) and every message a user or an agent sees are read in every repository that installs the kit, so they carry no ticket references. Where a rule or a line of code came from is written as a code comment that names the ticket in full (`RAL ticket 087`), or in `plugin/method/HISTORY.md` for the method. `tests/test_help_text.py` checks the help texts.

## Tests

Run from the kit folder; none needs a GPU or a model session. `tests/test_init.py` also runs real `claude plugin` commands against a scratch home when `claude` is on PATH.

```bash
for f in tests/test_*.py; do python3 -I "$f"; done
```

| Machine | Saved output |
|---|---|
| macOS 27 (arm64), no `setsid(1)` | `tests/runs/macos-2026-11-05-hashfix.txt` (all nine test files, the tree of the commit that adds it); earlier runs belong to earlier trees: `macos-2026-11-05.txt` (S5), `macos-2026-11-05-rev1.txt` (the tree RAL ticket 090 rev2 reviewed), `macos-2026-11-05-rev2.txt` (`cd92e8a`) |
| Linux work machine (host `usrg-sw-u20-Desktop`, Python 3.8), the tree that adds the outside-the-table warning (RAL ticket 090 Q-16) | `tests/runs/linux-2026-11-08-s11.txt` (all ten test files) |
| Linux work machine (host `usrg-sw-u20-Desktop`, Python 3.8), the tree that adds the same-quantity check (RAL ticket 090 Q-15, `e0a7925`) | `tests/runs/linux-2026-11-07-s10.txt` (all ten test files) |
| Linux work machine (host `usrg-sw-u20-Desktop`, Python 3.8), the tree that makes the cross-ticket citation check FAIL on unanswered items (RAL ticket 090 Q-14, `34d6ea0`) | `tests/runs/linux-2026-11-07-q14.txt` (all ten test files); the S8 tree before it (`2a6ec22`, warnings only): `linux-2026-11-07-s8.txt` |
| Linux work machine (host `usrg-sw-u20-Desktop`), at `cd92e8a` | `evidence/kit_tests_linux_cd92e8a.txt` in the RAL repository's ticket 090: 7 of 9 files pass; `test_qrispy_config` and `test_review_status` fail on the freeze bug this commit fixes |

A line that says a test ran somewhere must name the saved output of that run (the kit's lint warns on operating documents that do not).
