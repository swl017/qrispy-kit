#!/usr/bin/env python3
"""launch — start and list the workers an orchestrating session runs for its child tickets (RAL ticket 087, S3).

    launch.py prompt   --ticket "PAPER1 005" --parent "PAPER1 003" --parent-session NAME --agent claude|codex|gemini --task TEXT [--headless]
                       print the first prompt, filled from .claude/skills/orchestrate/templates/worker_prompt.md
    launch.py claude-bg --ticket "PAPER1 005" --prompt-file F [--worktree] [--dry-run]
                       a Claude background session named paper1-005 (`claude --bg -n`); the user joins with `claude attach paper1-005`
    launch.py headless --agent claude|codex|gemini --job DIR --prompt-file F [--dry-run]
                       a one-shot run (`claude -p`, `codex exec`, `gemini <prompt>`) under `qrispy job run` (lib/jobs/run_job.sh); output in DIR/job.log
    launch.py tmux     --agent codex|gemini --ticket "PAPER1 005" --prompt-file F [--cwd DIR] [--dry-run]
                       an interactive session of another agent in tmux session `agents`, window paper1-005 (RAL 087 Q-10:
                       agents without a named background session); the user joins with `tmux attach -t agents`
    Every command takes --root DIR: the repository or git worktree the worker runs in (default: this repository).
    launch.py result DIR   the final answer of a headless run (Claude runs log stream-json so their job.log grows while they work)
    launch.py watch --names a,b [--interval 20] [--heartbeat 300]   wait on Claude background workers: exits 0 when one waits
                       at a permission dialog, finishes its turn or is gone, 4 on the heartbeat; run it as a background command
    launch.py away on [--until HH:MM] | off | status   the user is away: watch and wait_job.sh stop waking the session,
                       events wait for one summary on return, new GPU runs are refused (RAL 087 Q-16)
    launch.py whoami [--json]   this session's name and session id (write both into the ticket you own; Q-17)
    launch.py status   every worker: Claude sessions (`claude agents --json`) and the windows of tmux session `agents`

Workers use this repository's settings; no flag that widens permissions (--dangerously-skip-permissions, --yolo,
--full-auto) is ever passed. Claude workers report with SendMessage; other agents append status lines to
<ticket>/jobs/worker/status.log (format `<ticket> <state>: <one line>`, states working | blocked | needs-decision | done | failed).
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys

LIB = os.path.dirname(os.path.abspath(__file__))  # the kit's tools (RAL 090)
sys.path.insert(0, LIB)
sys.dont_write_bytecode = True  # no lib/__pycache__ from the import below
import qrispy_config  # noqa: E402  ticket systems from qrispy.json (RAL 089)

TEMPLATE = os.path.join(qrispy_config.PLUGIN, "skills", "orchestrate", "templates", "worker_prompt.md")
RUN_JOB = os.path.join(LIB, "jobs", "run_job.sh")
CFG = qrispy_config.load_or_exit(None, "launch")  # finds the repository from the working folder (RAL 090)
REPO = CFG.repo
ROOTS = CFG.root_of
TMUX_SESSION = "agents"


def name_of(ticket):
    m = re.match(rf"^({CFG.names_alt()}) (\d{{3}})$", ticket)
    if not m:
        sys.exit(f"launch: ticket must look like '<{CFG.names_alt()}> NNN', got {ticket!r}")
    return f"{m.group(1).lower()}-{m.group(2)}"


def ticket_dir(ticket, root=REPO):
    name_of(ticket)  # an unknown system stops here with the usage line, not a KeyError (RAL 089)
    system, num = ticket.split()
    base = os.path.join(root, ROOTS[system])
    hits = [d for d in os.listdir(base) if d.startswith(num + "-")] if os.path.isdir(base) else []
    return os.path.join(ROOTS[system], hits[0]) if len(hits) == 1 else f"{ROOTS[system]}/{num}-<slug>"


def short(s, n=160):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def run(cmd, dry, cwd=REPO):
    print("$ " + " ".join(shlex.quote(c) for c in cmd))
    if dry:
        return 0
    return subprocess.run(cmd, cwd=cwd).returncode


def read_prompt(path):
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def cmd_prompt(a):
    with open(TEMPLATE, encoding="utf-8") as f:
        t = f.read()
    tdir = ticket_dir(a.ticket, a.root)
    report = ("Report to the parent session with SendMessage (to: " + a.parent_session + "), one status line per message."
              if a.agent == "claude" else
              "You cannot message other sessions. End your final answer with your status lines." if a.headless else
              f"You cannot message other sessions. Append each status line to {tdir}/jobs/worker/status.log (create the folder if needed).")
    vals = {"ticket": a.ticket, "ticket_dir": tdir, "parent": a.parent, "parent_session": a.parent_session,
            "name": name_of(a.ticket), "report": report, "task": a.task.strip(),
            # a headless run has nobody to answer a permission dialog, so it edits nothing: its result is its final
            # answer (job.log) and the orchestrator files it (RAL 087 S3 live test)
            "setup2": ("You run headless: do not edit any file and do not write `session`; your final answer is your result. Nobody can answer a permission dialog here, so a call that needs one is refused: report it as `blocked: <what was refused>` and say what you could not do, rather than quietly narrowing the task."
                       if a.headless else f'Run `qrispy worker whoami` and write its two lines into your ticket\'s `state.json` (`session`, `session_id`; your name should be {name_of(a.ticket)}).'),
            # RAL 087 S4 pilot notes: a headless worker cannot write Q items, and every interactive worker must record a
            # decision the user gives it directly and tell the parent
            "decision_rule": ("A decision that belongs to the user: put the proposed Q item (question, options, your recommendation) in your final answer and report `needs-decision`; the parent writes it into the ticket."
                              if a.headless else
                              "A decision that belongs to the user goes into your ticket's `q_questions.md` as a Q item with a recommendation; then report `needs-decision`."),
            "user_decision": ("" if a.headless else
                              f"\n- The user may answer you directly (they can attach to your session). Copy the answer verbatim into your ticket's `q_questions.md` under `> 사용자 답 (<date>, <channel>):` with the decision line, then report `{a.ticket} decision: Q-n = <gist>` to the parent."),
            # RAL 087 S4 pilot note 7: a worker read a permission dialog as "edits are blocked in the shared checkout" and
            # moved itself and its ticket files into a worktree, leaving the parent a stale copy on main
            "stay": ("Stay in the directory you were started in; never create or enter a git worktree yourself. A permission dialog or a refusal is not a reason to move: report `blocked: <what>` and wait for the user. "
                     f"Your ticket files live only in the main checkout ({os.path.join(a.main_root, tdir)}); if you were started in a worktree for code, still write ticket files there."),
            # RAL 087 S4 pilot note 15: siblings had no path to align a design, so the parent relayed by hand
            "siblings": ("Other workers under " + a.parent + " are your siblings (`qrispy show " + a.parent + "` lists them; a Claude background worker is named like `paper1-005`). "
                         + ("Put any alignment item for a sibling in your final answer; the parent passes it on."
                            if a.headless or a.agent != "claude" else
                            "For a technical alignment item (an interface, a file format, a shared definition), message that sibling directly with SendMessage and send the parent a one-line copy `" + a.ticket + " aligned with <sibling>: <gist>`. Anything that would change another ticket's scope or acceptance criteria, or needs the user, goes to the parent instead.")),
            "finish": ("When the task is finished, put the whole result in your final answer (it lands in the job log; the parent files it), and report `done`."
                       if a.headless else "When the task is finished, write the slice note or closeout your ticket needs, update `state.json`, and send `done`.")}
    out = re.sub(r"\{(\w+)\}", lambda m: vals.get(m.group(1), m.group(0)), t)
    body = out.split("<!-- prompt -->", 1)[-1].strip()
    print(body)


def cmd_claude_bg(a):
    n = name_of(a.ticket)
    cmd = ["claude", "--bg", "-n", n] + (["--worktree", n] if a.worktree else []) + [read_prompt(a.prompt_file)]
    if a.dry_run:
        sys.exit(run(cmd, True))
    print("$ " + " ".join(shlex.quote(c) for c in cmd[:-1]) + " <prompt>")
    r = subprocess.run(cmd, cwd=a.root, capture_output=True, text=True)
    print((r.stdout + r.stderr).strip())
    # `claude --bg` exits 0 even when it starts nothing (e.g. "Workspace not trusted"): check its own report
    rc = 0 if r.returncode == 0 and "backgrounded" in r.stdout else 1
    if rc:
        print(f"launch: {n} did not start; a worker runs only in a workspace Claude Code trusts (this repository or its worktrees)", file=sys.stderr)
    else:
        print(f"started {n}: join with `claude attach {n}`; it should write `\"session\": \"{n}\"` into its state.json")
    sys.exit(rc)


def cmd_headless(a):
    p = read_prompt(a.prompt_file)
    m = re.search(rf"({CFG.roots_alt()})/(\d{{3}})-[^/]+/jobs/([^/]+)/?$", os.path.abspath(a.job))
    sysname = CFG.system_of_root[m.group(1)].lower() if m else "job"
    hname = f"{sysname}-{m.group(2)}-{m.group(3)}" if m else os.path.basename(a.job)
    # no --permission-mode: a worker runs in the user's normal mode, like an interactive session (RAL 087 S3 live test;
    # `default` is for read-only reviewers and refuses every edit in a session nobody can answer)
    # stream-json: job.log grows while the worker works, so a heartbeat can tell working from stuck (RAL 087 S4 pilot
    # note 3); `launch.py result <job dir>` pulls the final answer out of it
    agent = {"claude": ["claude", "-p", "-n", hname, "--output-format", "stream-json", "--verbose", p],
             "codex": ["codex", "exec", p],
             "gemini": ["gemini", p]}[a.agent]
    sys.exit(run([RUN_JOB, os.path.abspath(a.job), "--next", f"read the {a.agent} worker output in job.log", "--"] + agent, a.dry_run, cwd=a.root))


def cmd_tmux(a):
    n, p = name_of(a.ticket), read_prompt(a.prompt_file)
    agent = {"codex": ["codex", p], "gemini": ["gemini", "-i", p]}[a.agent]
    cwd = os.path.abspath(a.cwd or a.root)
    has = subprocess.run(["tmux", "has-session", "-t", TMUX_SESSION], capture_output=True).returncode == 0
    if not has:
        run(["tmux", "new-session", "-d", "-s", TMUX_SESSION, "-n", "home", "-c", cwd], a.dry_run)
    rc = run(["tmux", "new-window", "-d", "-t", TMUX_SESSION, "-n", n, "-c", cwd, shlex.join(agent)], a.dry_run)
    if rc == 0 and not a.dry_run:
        print(f"started {n} in tmux session {TMUX_SESSION}: join with `tmux attach -t {TMUX_SESSION}` (window {n})")
    sys.exit(rc)


def cmd_result(a):
    """Final answer of a headless Claude worker from its stream-json job.log, then one stats line; any other log as is."""
    log = os.path.join(a.job, "job.log")
    with open(log, encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    res, calls, last = None, 0, ""
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            for c in e.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    calls += 1
                elif c.get("type") == "text":
                    last = c.get("text", "")
        if e.get("type") == "result":
            res = e
    if res is None and not last:
        sys.stdout.write("".join(lines))  # not a stream: codex, gemini, or an older run
        return
    print((res or {}).get("result") or last)
    if res:
        den = res.get("permission_denials") or []
        print(f"\n[{os.path.basename(os.path.abspath(a.job))}: {res.get('subtype')}, tool_calls={calls}, turns={res.get('num_turns')}, "
              f"denials={len(den)}, cost_usd={res.get('total_cost_usd') or 0:.2f}]")
        if den:  # a headless run has no dialog: refused calls are silent unless shown here (RAL 087 S4 pilot note 4)
            print(f"WARN  {len(den)} tool calls were refused; the worker could not do them and may have narrowed its task. Tell the user:")
            for d in den:
                inp = d.get("tool_input") or {}
                what = inp.get("command") or inp.get("file_path") or json.dumps(inp, ensure_ascii=False)
                print(f"  - {d.get('tool_name', '?')}: {short(what)}")
    else:
        print(f"\n[{os.path.basename(os.path.abspath(a.job))}: no result event yet (still running or died); tool_calls={calls}]")


LOCK_DIR = lambda: os.path.expanduser(os.environ.get("AGENT_LOCK_DIR", "~/.agent_locks"))  # noqa: E731
AWAY_NOTICE = ("The user is away (launch.py away, RAL 087 Q-16). Finish the step you are on, then stop and wait. Until you are told the user "
               "is back, do not ask or notify the user and do not start a GPU run; leave anything for them as status lines or in your ticket files.")
BACK_NOTICE = "The user is back (launch.py away off). Continue your task from where you stopped."


def away_state():
    """The away record, or None when the user is here (no file, or its --until time has passed)."""
    import datetime
    try:
        with open(os.path.join(LOCK_DIR(), "away.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    until = d.get("until")
    if until:
        try:
            if datetime.datetime.now().astimezone() >= datetime.datetime.fromisoformat(until):
                return None
        except ValueError:
            pass
    return d


def away_event(text):
    """Keep an event for the summary the user gets on return, instead of waking anyone."""
    import time
    os.makedirs(LOCK_DIR(), exist_ok=True)
    with open(os.path.join(LOCK_DIR(), "away_events.log"), "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {text}\n")


def cmd_away(a):
    """away on [--until HH:MM] [--note TEXT] | off | status | active (exit 0 when away, 1 when not; for scripts)."""
    import datetime
    path, log = os.path.join(LOCK_DIR(), "away.json"), os.path.join(LOCK_DIR(), "away_events.log")
    if a.mode == "on":
        now = datetime.datetime.now().astimezone()
        until = None
        if a.until:
            hh, mm = map(int, a.until.split(":"))
            u = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            until = (u if u > now else u + datetime.timedelta(days=1)).isoformat(timespec="seconds")
        os.makedirs(LOCK_DIR(), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"since": now.isoformat(timespec="seconds"), "until": until, "note": a.note or ""}, f)
        print(f"away since {now:%H:%M}" + (f" until {until[11:16]}" if until else "") + ". Watchers stop waking you; events go to the return summary; new GPU runs are refused.")
        print("Send each running worker this message (SendMessage), and tell the user nothing more until they are back:")
        print(AWAY_NOTICE)
    elif a.mode == "off":
        d = away_state()
        try:
            os.remove(path)
        except OSError:
            pass
        events = open(log, encoding="utf-8").read().splitlines() if os.path.exists(log) else []
        if os.path.exists(log):
            os.replace(log, log.replace(".log", f".{datetime.datetime.now():%Y%m%d-%H%M%S}.log"))
        print(f"back. Away since {(d or {}).get('since', '?')[11:16]}; {len(events)} events while away:")
        for e in events:
            print("  " + e)
        print("Send each worker: " + BACK_NOTICE)
        print("Then give the user one summary: what finished, what waits on them, what they must decide (gather decisions with `qrispy questions`).")
    else:
        d = away_state()
        if a.mode == "active":
            sys.exit(0 if d else 1)
        print(f"away since {d['since'][11:16]}" + (f" until {d['until'][11:16]}" if d.get("until") else "") + (f" — {d['note']}" if d.get("note") else "") if d else "here (not away)")


def agent_rows():
    """`claude agents --json` rows; QRISPY_AGENTS_JSON=<file> replaces the call (tests). None when unreadable."""
    try:
        fake = os.environ.get("QRISPY_AGENTS_JSON")
        if fake:
            with open(fake, encoding="utf-8") as f:
                return json.load(f)
        return json.loads(subprocess.run(["claude", "agents", "--json"], capture_output=True, text=True, timeout=15).stdout)
    except Exception:  # noqa: BLE001
        return None


SPINNER = re.compile(r"[↓↑]\s*([0-9.]+)(k?)\s*tokens")


def spinner_tokens(text):
    """Output-token count of the last spinner reading on a Claude Code screen, e.g. '… · ↓ 57.7k tokens)' -> 57700;
    None if absent. The screen is redrawn in pieces, so the elapsed-time part is often cut and is not read."""
    hits = SPINNER.findall(re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text))
    if not hits:
        return None
    n, k = hits[-1]
    return int(float(n) * (1000 if k else 1))


def progress(row):
    """Signs of life of a Claude background worker (RAL 087 S4 pilot note 14): age of its transcript file and the
    spinner's output-token count on its screen. A long generation moves the tokens; a hang moves neither."""
    import glob as _g
    import time
    out = []
    sid = row.get("sessionId")
    files = _g.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl")) if sid else []
    if files:
        out.append(f"transcript {int(time.time() - max(os.path.getmtime(f) for f in files))} s ago")
    if row.get("kind") == "background" and row.get("id") and row.get("status") == "busy":
        try:
            screen = subprocess.run(["claude", "logs", str(row["id"])], capture_output=True, text=True, timeout=15).stdout
            sp = spinner_tokens(screen)
            if sp:
                out.append(f"spinner at {sp} output tokens")
        except Exception:  # noqa: BLE001
            pass
    return "; ".join(out)


def worker_ticket_dir(name, root):
    m = re.match(rf"^({CFG.names_alt().lower()})-(\d{{3}})$", name or "")
    if not m:
        return None
    base = os.path.join(root, ROOTS[m.group(1).upper()])
    dirs = [os.path.join(base, d) for d in (os.listdir(base) if os.path.isdir(base) else []) if d.startswith(m.group(2) + "-")]
    return dirs[0] if len(dirs) == 1 else None


def ticket_line(name, root):
    """'ticket PAPER1 007: stage Q, owes the user 10' for a worker named paper1-007, from its state.json; "" if none.
    The harness says only whether the session's last turn ended; the ticket says whether the work is done (RAL 087 S4
    pilot note 16)."""
    d = worker_ticket_dir(name, root)
    if not d:
        return ""
    try:
        with open(os.path.join(d, "state.json"), encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        return ""
    owes = s.get("awaiting_user") if isinstance(s.get("awaiting_user"), list) else []
    return f"ticket {name.split('-')[0].upper()} {name.split('-')[1]}: stage {str(s.get('current_stage', '?'))[:24]}, owes the user {len(owes)}"


def ticket_signature(name, root):
    """Latest mtime under the ticket folder that a worker name like paper1-006 stands for, or None (RAL 087 S4 pilot
    note 13: a worker waiting on the user ends turns without changing anything)."""
    d = worker_ticket_dir(name, root)
    if not d:
        return None
    latest = 0.0
    for dp, _, fs in os.walk(d):
        for f in fs:
            try:
                latest = max(latest, os.path.getmtime(os.path.join(dp, f)))
            except OSError:
                pass
    return latest


def cmd_watch(a):
    """Wait on Claude background workers; exit (waking the session that runs this as a background command) on the first
    worker that waits at a permission dialog, finishes its turn, or is gone. notify_when_idle does not fire for a worker
    stopped at a dialog, because it is not idle (RAL 087 S4 pilot note 5). Exit 0 on an event, 4 on the heartbeat."""
    import time
    names = [n for n in a.names.split(",") if n]
    start, seen_busy = time.time(), set()
    # waits already reported survive a re-arm, so a worker still at the same dialog does not wake us again at once;
    # the next event for it is the dialog being answered (RAL 087 S4 pilot note 9)
    seen_file = a.seen_file or os.path.join(os.path.expanduser(os.environ.get("AGENT_LOCK_DIR", "~/.agent_locks")), "watch_seen.json")
    try:
        with open(seen_file, encoding="utf-8") as f:
            state = json.load(f)
        state = state if isinstance(state, dict) else {"waiting": state, "idle": {}}  # older form: a list of waits
    except (OSError, ValueError):
        state = {"waiting": [], "idle": {}}
    reported = set(state.get("waiting", []))
    idle_sig = dict(state.get("idle", {}))  # worker -> ticket signature when its idle turn was last reported

    def save(s, idle=None):
        os.makedirs(os.path.dirname(seen_file), exist_ok=True)
        with open(seen_file, "w", encoding="utf-8") as f:
            json.dump({"waiting": sorted(s), "idle": idle if idle is not None else idle_sig}, f)
    was_away = False
    while True:
        rows = agent_rows()
        now = time.strftime("%H:%M:%S")
        away = away_state() is not None
        if was_away and not away:
            print(f"{now} the user is back: read `launch.py away off` (or the events in ~/.agent_locks) and give one summary"); sys.exit(0)
        was_away = away
        if rows is not None:
            cur = {str(r.get("name")): r for r in rows}
            for n in names:
                r = cur.get(n)
                if r is None:
                    if away:
                        if n not in reported:
                            away_event(f"{n}: not running"); reported.add(n); save(reported)
                        continue
                    print(f"{now} {n}: not running (stopped, removed or crashed)"); sys.exit(0)
                if r.get("waitingFor"):
                    if n not in reported:
                        save(reported | {n})
                        if away:  # the user is away: keep it for the return summary, wake nobody (Q-16)
                            reported.add(n); away_event(f"{n}: waiting for {r['waitingFor']}"); continue
                        print(f"{now} {n}: waiting for {r['waitingFor']} — tell the user now: claude attach {n}"); sys.exit(0)
                    continue  # already reported; wait for it to clear
                if n in reported:
                    save(reported - {n})
                    print(f"{now} {n}: the dialog was answered; it is {r.get('status')} again"); sys.exit(0)
                if r.get("status") == "busy":
                    seen_busy.add(n)
                elif r.get("status") == "idle" and (n in seen_busy or time.time() - start > a.settle):
                    sig = ticket_signature(n, a.root)
                    if sig is not None and idle_sig.get(n) == sig:
                        continue  # ended another turn without touching its ticket: a worker waiting on the user
                    save(reported, {**idle_sig, n: sig})
                    if away:
                        idle_sig[n] = sig; away_event(f"{n}: ended a turn ({ticket_line(n, a.root) or 'no ticket'})"); continue
                    tl = ticket_line(n, a.root)
                    print(f"{now} {n}: session idle, its turn ended (harness state {r.get('state') or '-'}, not the worker's `done`) — read its last status line" + (f"; {tl}" if tl else "")); sys.exit(0)
        if away:
            start = time.time()  # no heartbeat while the user is away
        if time.time() - start >= a.heartbeat:
            state = "unknown (claude agents unreadable)" if rows is None else ", ".join(
                f"{n} {(cur.get(n) or {}).get('status', 'gone')}" + (" (still at the reported dialog)" if n in reported else "")
                + (f" [{progress(cur[n])}]" if n in cur and not os.environ.get("QRISPY_AGENTS_JSON") else "") for n in names)
            print(f"{now} heartbeat: {state}"); sys.exit(4)
        time.sleep(a.interval)


def cmd_whoami(a):
    """This session's name and id: the Claude process among this shell's ancestors, matched against `claude agents
    --json`. Write both into the ticket you own (`session`, `session_id`): the name changes when a session reopens, the
    id does not (RAL 087 Q-17)."""
    rows = agent_rows() or []
    bypid = {int(r["pid"]): r for r in rows if str(r.get("pid", "")).isdigit()}
    pid = os.getpid()
    for _ in range(64):
        if pid in bypid:
            r = bypid[pid]
            if a.json:
                print(json.dumps({"session": r.get("name"), "session_id": r.get("sessionId"), "kind": r.get("kind")}))
            else:
                print(f"session    {r.get('name')}\nsession_id {r.get('sessionId')}\nkind       {r.get('kind')}")
            return
        pid = qrispy_config.parent_pid(pid)  # /proc, else ps (macOS, RAL 089)
        if pid is None or pid <= 1:
            break
    sys.exit("launch: this shell is not inside a Claude session that `claude agents --json` lists")


def cmd_status(a):
    try:
        raw = subprocess.run(["claude", "agents", "--json"], capture_output=True, text=True, timeout=15).stdout
        rows = json.loads(raw)
        print(f"claude sessions: {len(rows)} (session busy/idle and 'last turn …' are the harness's; the worker's own state is in its status lines and ticket)")
        for s in rows:
            wait = f" ({s['waitingFor']})" if s.get("waitingFor") else ""
            prog = progress(s) if s.get("kind") == "background" else ""
            tl = ticket_line(str(s.get("name")), a.root)
            turn = f", last turn {s['state']}" if s.get("state") else ""
            print(f"  {s.get('name'):<40} {s.get('kind', '?'):<11} session {s.get('status', '?')}{wait}{turn}"
                  + (f"  [{prog}]" if prog else "") + (f"  | {tl}" if tl else ""))
    except Exception as e:  # noqa: BLE001
        print(f"claude sessions: unknown ({type(e).__name__})")
    r = subprocess.run(["tmux", "list-windows", "-t", TMUX_SESSION, "-F", "#{window_name}\t#{pane_dead}\t#{pane_current_command}"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"tmux session {TMUX_SESSION}: none")
        return
    wins = [w.split("\t") for w in r.stdout.splitlines() if not w.startswith("home\t")]
    print(f"tmux session {TMUX_SESSION}: {len(wins)} worker windows")
    for name, dead, cmdname in wins:
        print(f"  {name:<40} {'dead' if dead == '1' else 'alive'} ({cmdname})")


def main(argv):
    ap = argparse.ArgumentParser(prog="launch.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prompt")
    for k in ("--ticket", "--parent", "--parent-session", "--task"):
        p.add_argument(k, required=True)
    p.add_argument("--agent", required=True, choices=("claude", "codex", "gemini"))
    p.add_argument("--headless", action="store_true", help="for launch.py headless: edit nothing, answer with the result")
    p.add_argument("--main-root", default=REPO, help="the main checkout that holds the ticket files (default: this repository)")
    p = sub.add_parser("claude-bg"); p.add_argument("--ticket", required=True); p.add_argument("--prompt-file", required=True)
    p.add_argument("--worktree", action="store_true"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("headless"); p.add_argument("--agent", required=True, choices=("claude", "codex", "gemini"))
    p.add_argument("--job", required=True); p.add_argument("--prompt-file", required=True); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("tmux"); p.add_argument("--agent", required=True, choices=("codex", "gemini"))
    p.add_argument("--ticket", required=True); p.add_argument("--prompt-file", required=True); p.add_argument("--cwd")
    p.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    p = sub.add_parser("whoami"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("result"); p.add_argument("job", help="job dir of a headless run")
    p = sub.add_parser("away"); p.add_argument("mode", choices=("on", "off", "status", "active"))
    p.add_argument("--until", help="HH:MM, local; away ends by itself then"); p.add_argument("--note")
    p = sub.add_parser("watch"); p.add_argument("--names", required=True, help="comma-separated worker names")
    p.add_argument("--interval", type=float, default=20); p.add_argument("--heartbeat", type=float, default=300)
    p.add_argument("--settle", type=float, default=60, help="seconds before an idle worker never seen busy counts as finished")
    p.add_argument("--seen-file", help="where reported waits are kept between runs (default ~/.agent_locks/watch_seen.json)")
    for sp in sub.choices.values():  # the repository (or worktree) the worker runs in; default: this one
        sp.add_argument("--root", default=REPO)
    a = ap.parse_args(argv)
    a.root = os.path.abspath(a.root)
    {"prompt": cmd_prompt, "claude-bg": cmd_claude_bg, "headless": cmd_headless, "tmux": cmd_tmux, "status": cmd_status, "result": cmd_result, "watch": cmd_watch, "away": cmd_away, "whoami": cmd_whoami}[a.cmd](a)


if __name__ == "__main__":
    main(sys.argv[1:])
