#!/usr/bin/env python3
"""gpu_lock — who is using this machine's GPU, for which ticket, and whether it is running or only held (RAL ticket 087, S2).

    gpu_lock.py status [--json]                               one line: free | running | held | ownerless (+ owner, since, note)
    gpu_lock.py take --kind sim|train|other (--ticket "PAPER1 006" --session NAME | --job DIR) [--note TEXT]
    gpu_lock.py hold (--session NAME | --job DIR) [--note TEXT]   the run ended but the owner keeps the GPU (e.g. the sim stays up)
    gpu_lock.py note --session NAME TEXT                       change the one-line note
    gpu_lock.py release --session NAME [--force]              nobody uses the GPU any more (--force: user-approved, any owner)

One GPU (RTX 3090) serves both Isaac Sim and IsaacLab training, so there is one lock, `gpu`, with a `kind` (RAL 087 Q-11).
The lock warns, it never blocks a process: `take` refuses with exit code 3 and names the owner, and the caller asks the
user (Q-6). States: `running` (a job under the lock is alive), `held` (between runs, the owner keeps it), free (no file).
`ownerless`: running but the job is gone without DONE.json, or held by a session that is not running and silent for
over 2 hours. Deleting an ownerless lock is the user's call (`release --force`).

File: $AGENT_LOCK_DIR/gpu.json (default ~/.agent_locks/, outside every repository so mas_fieldtest, PegasusSimulator
and IsaacLab work see the same lock). Writes hold an flock on gpu.lock and replace the file atomically.
QRISPY_AGENTS_JSON=<file> replaces `claude agents --json` (tests).
"""
import argparse
import datetime
import fcntl
import json
import os
import subprocess
import sys
import tempfile

LOCK_DIR = os.path.expanduser(os.environ.get("AGENT_LOCK_DIR", "~/.agent_locks"))
PATH = os.path.join(LOCK_DIR, "gpu.json")
HELD_SILENT_S = 2 * 3600
KINDS = ("sim", "train", "other")
REFUSED = 3


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def age_s(ts):
    try:
        return (datetime.datetime.now().astimezone() - datetime.datetime.fromisoformat(ts)).total_seconds()
    except (TypeError, ValueError):
        return float("inf")


def read():
    try:
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def write(d):
    os.makedirs(LOCK_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=LOCK_DIR, prefix=".gpu.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, PATH)


class Locked:
    """Serialise read-modify-write between processes."""
    def __enter__(self):
        os.makedirs(LOCK_DIR, exist_ok=True)
        self.f = open(os.path.join(LOCK_DIR, "gpu.lock"), "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def sessions():
    """Names of running Claude sessions, or None when that cannot be read."""
    try:
        fake = os.environ.get("QRISPY_AGENTS_JSON")
        if fake:
            with open(fake, encoding="utf-8") as f:
                raw = f.read()
        else:
            raw = subprocess.run(["claude", "agents", "--json"], capture_output=True, text=True, timeout=15).stdout
        return {str(s.get("name")) for s in json.loads(raw)}
    except Exception:  # noqa: BLE001
        return None


def job_alive(job):
    """True / False for a run_job.sh job dir, None when unknown."""
    if not job:
        return None
    if not os.path.isdir(job):
        return False  # the job dir itself is gone
    if os.path.exists(os.path.join(job, "DONE.json")):
        return False
    try:
        with open(os.path.join(job, "pid")) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # qrispy_config sits next to this file in the kit (RAL 090)
    sys.dont_write_bytecode = True  # no lib/__pycache__ from the import below
    import qrispy_config  # pid_alive: os.kill, not /proc, which macOS lacks (RAL 089); needs no qrispy.json
    return qrispy_config.pid_alive(pid)


def judge(d):
    """(state, reason): state is free | running | held | ownerless."""
    if d is None:
        return "free", ""
    if d.get("state") == "running":
        alive = job_alive(d.get("job_dir"))
        if alive is False and not os.path.exists(os.path.join(d.get("job_dir") or "", "DONE.json")):
            return "ownerless", "its job is gone without DONE.json"
        if alive is False:
            return "held", "its job ended; run_job.sh did not set held (treat as held)"
        return "running", ""
    if d.get("state") == "held":
        live = sessions()
        if live is not None and d.get("session") not in live and age_s(d.get("updated")) > HELD_SILENT_S:
            return "ownerless", f"session {d.get('session')} is not running and the lock is silent for over 2 h"
        return "held", ""
    return "ownerless", f"unknown state {d.get('state')!r}"


def user_away():
    """The away record from lib/launch.py away on (`qrispy worker away on`), or None (RAL 087 Q-16)."""
    try:
        with open(os.path.join(LOCK_DIR, "away.json"), encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None
    if d.get("until") and age_s(d["until"]) >= 0:
        return None
    return d


def from_job(job):
    """(ticket, session) of a run_job.sh job dir <...>/<NNN-slug>/jobs/<id>: the ticket's system from its tickets
    folder, the session from its state.json (else $AGENT_SESSION, else "unknown")."""
    tdir = os.path.dirname(os.path.dirname(os.path.abspath(job)))
    root, slug = os.path.dirname(tdir), os.path.basename(tdir)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # qrispy_config sits next to this file in the kit (RAL 090)
    sys.dont_write_bytecode = True  # no lib/__pycache__ from the import below
    import qrispy_config  # ticket systems from qrispy.json (RAL 089); loaded here so `status` needs no config
    try:  # the repository is the one the job dir sits in, wherever the lock is taken from (RAL 090)
        repo = qrispy_config.find_repo(os.path.abspath(job))
    except qrispy_config.ConfigError as e:
        sys.exit(f"gpu_lock: {e}")
    cfg = qrispy_config.load_or_exit(repo, prog="gpu_lock")
    system = cfg.system_of_dir(root) or cfg.primary
    session = None
    try:
        with open(os.path.join(tdir, "state.json"), encoding="utf-8") as f:
            session = json.load(f).get("session")
    except (OSError, ValueError):
        pass
    return f"{system} {slug[:3]}", session or os.environ.get("AGENT_SESSION") or "unknown"


def line(d):
    st, why = judge(d)
    if st == "free":
        return "gpu: free"
    s = (f"gpu: {st} by {d.get('ticket')} (session {d.get('session')}, {d.get('kind')}) since {str(d.get('since'))[11:16]}"
         f" — {d.get('note') or '-'}")
    return s + (f" [{why}]" if why else "")


def refuse(d, what):
    print(f"gpu_lock: {what} refused — {line(d)}. Ask the user before going on (RAL 087 Q-6).", file=sys.stderr)
    sys.exit(REFUSED)


def main(argv):
    ap = argparse.ArgumentParser(prog="gpu_lock.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("take")
    p.add_argument("--kind", required=True, choices=KINDS); p.add_argument("--ticket"); p.add_argument("--session")
    p.add_argument("--note", default=""); p.add_argument("--job", default="", help="run_job.sh job dir; gives ticket and session when omitted")
    p = sub.add_parser("hold"); p.add_argument("--session"); p.add_argument("--note"); p.add_argument("--job", default="")
    p = sub.add_parser("note"); p.add_argument("--session", required=True); p.add_argument("text")
    p = sub.add_parser("release"); p.add_argument("--session", required=True); p.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd in ("take", "hold") and getattr(a, "job", ""):
        tk, ss = from_job(a.job)
        a.session = a.session or ss
        if a.cmd == "take":
            a.ticket = a.ticket or tk
    if a.cmd in ("take", "hold") and not a.session or a.cmd == "take" and not a.ticket:
        sys.exit("gpu_lock: give --ticket and --session, or --job <run_job dir>")

    if a.cmd == "status":
        d = read()
        if a.json:
            st, why = judge(d)
            print(json.dumps({"state": st, "reason": why, "lock": d}, ensure_ascii=False))
        else:
            print(line(d))
        return

    with Locked():
        d = read()
        st, _ = judge(d)
        if a.cmd == "take":
            away = user_away()
            if away:
                print(f"gpu_lock: take refused — the user is away since {str(away.get('since'))[11:16]} (launch.py away); no new GPU run until they are back (RAL 087 Q-16).", file=sys.stderr)
                sys.exit(REFUSED)
            job = os.path.abspath(a.job) if a.job else ""
            if st in ("running", "held", "ownerless") and d.get("session") != a.session:
                refuse(d, "take")
            if st == "running" and d.get("job_dir") and d.get("job_dir") != job:
                refuse(d, "take (your own earlier job still runs)")
            t = now()
            write({"resource": "gpu", "state": "running" if job else "held", "kind": a.kind, "ticket": a.ticket,
                   "session": a.session, "job_dir": job, "since": d.get("since") if d and d.get("session") == a.session else t,
                   "updated": t, "note": a.note or (d or {}).get("note", "")})
        elif a.cmd == "hold":
            if d is None:
                sys.exit("gpu_lock: nothing to hold (free)")
            if d.get("session") != a.session:
                refuse(d, "hold")
            if a.job and d.get("job_dir") and os.path.abspath(a.job) != d.get("job_dir"):
                return  # the lock moved on to another job of the same owner; leave it
            d.update(state="held", job_dir="", updated=now())
            if a.note is not None:
                d["note"] = a.note
            write(d)
        elif a.cmd == "note":
            if d is None or d.get("session") != a.session:
                refuse(d or {}, "note") if d else sys.exit("gpu_lock: free; nothing to note")
            d.update(note=a.text, updated=now())
            write(d)
        elif a.cmd == "release":
            if d is None:
                print("gpu: free (nothing to release)")
                return
            if d.get("session") != a.session and not a.force:
                refuse(d, "release")
            os.remove(PATH)
    print(line(read()))


if __name__ == "__main__":
    main(sys.argv[1:])
