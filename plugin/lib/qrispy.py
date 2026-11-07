#!/usr/bin/env python3
"""qrispy — the status view of QRISPY tickets, and the entry to the kit's other tools (see `qrispy help`).

    qrispy ls [--recent | --all | --parked] [--<system> ...]   (--parked: grouped by revisit trigger)   one line per ticket (default: open tickets of both systems)
    qrispy ls --tree [--all] [--<system> ...]   project → parent → child tickets (state.json.parent), with each owning session and whether it runs
    qrispy show <id>                        one ticket's status card (with its parent, its children, and whether the owning sessions run)
    qrispy inbox                            everything the user owes, across tickets
    qrispy cite <id>                        the ticket's citation boundary (CITE.md, else what exists)
    qrispy lint <id> | --repo               registry checks (PASS/FAIL lines); --repo checks memory-file sizes
    qrispy questions --tree <id> [--html <out.html>]   every unanswered Q item of a ticket and its children on one decision page
    qrispy dashboard --html <out.html>      one static page: what the user owes, running jobs, roadmap items and the tickets serving them, recent tickets (open it with Lavish)

<id> is a number (`084`, `DEMO 084`, `SIDE 017`, `DEMO 001`) or a slug fragment. This tool reports; it never gates,
never writes a ticket file, and never rewrites an old state.json (`dashboard` writes only the page named by --html). Fields it cannot find are shown as `?`.
Output is compact on purpose (agent-facing): no decoration, one item per line, counts first.
"""
# Provenance (kept out of the help text, which every repository prints): RAL ticket 084 S3 (named `qr` until 2026-10-15); the tree view RAL ticket 087; questions --tree RAL ticket 087 Q-15.
import glob
import json
import os
import re
import sys

LIB = os.path.dirname(os.path.abspath(__file__))  # the kit's tools (RAL ticket 090: they no longer live in the repository)
sys.path.insert(0, LIB)
sys.dont_write_bytecode = True  # no lib/__pycache__ from the import below
import qrispy_config  # noqa: E402  ticket systems from qrispy.json (RAL ticket 089)

CFG = qrispy_config.load_or_exit()  # finds the repository from the working folder (RAL ticket 090)
REPO = CFG.repo
ROOTS = CFG.abs_roots()
SYSTEMS = CFG.names_alt()
V2_DATE = "2026-10-14"
CLOSED_RE = re.compile(r"^[\W_]*(closed|superseded)\b", re.I)  # tolerate leading ⚠, **, etc.
PARKED_RE = re.compile(r"\bparked\b", re.I)
STALE_DAYS = 30
KNOWN_DUP_NUMBERS = CFG.known_dups  # e.g. RAL ticket 036-dual and 036-pm predate the check; always named by slug
# Project roadmap ledger (RAL ticket 086; tickets/QRISPY_METHOD.md §Project Roadmap)
LEDGER_ID = re.compile(r"^(Item|Claim|Exp|Gap|Decision|Risk)-\d+[a-z]?$")
TICKET_REF = re.compile(rf"\b({SYSTEMS}) (\d{{3}})\b")
ROADMAP_STATUSES = ("planned", "active", "done", "parked", "dropped")
_ROADMAPS = {}
# Parent and child tickets (RAL ticket 087 Q-4): only the child names its parent, as "<SYSTEM> NNN"
PARENT_RE = re.compile(rf"^({SYSTEMS}) (\d{{3}})$")
LEGACY_PARENT_RE = re.compile(rf"^(?:({CFG.roots_alt()})/)?(\d{{3}})-[\w.-]+/?$")
LEGACY_ROOTS = CFG.system_of_root
TITLE_PREFIX_RE = re.compile(rf"^(?:(?:{CFG.names_alt(external=True)})\s*)?(?:ticket\s*)?\d+\s*[—:-]\s*", re.I)
_AGENTS = []
_SESSION_IDS = {}  # sessionId -> current name (RAL ticket 087 Q-17: a name changes when a session reopens, its id does not)


def roadmap(system):
    """{ID: {"status", "owners", "section"}} from the ledger tables of the project's ROADMAP.md
    (the file next to the system's tickets/ folder), or None when the project has no roadmap."""
    if system in _ROADMAPS:
        return _ROADMAPS[system]
    root = dict(ROOTS).get(system)
    path = os.path.join(os.path.dirname(root), "ROADMAP.md") if root else ""
    if not os.path.exists(path):
        _ROADMAPS[system] = None
        return None
    items, header, section = {}, None, ""
    with open(path, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("## "):
                section, header = s[3:], None
                continue
            if not s.startswith("|"):
                header = None
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if header is None:
                header = cells
                continue
            if not "".join(cells).strip("-: "):
                continue  # the |---|---| separator row
            key = cells[0].strip("`* ")
            if LEDGER_ID.match(key):
                row = dict(zip(header, cells))
                status = row.get("상태", "").strip("`* ").lower() or None
                items[key] = {"status": status, "owners": [f"{a} {b}" for a, b in TICKET_REF.findall(row.get("담당", ""))],
                              "section": section}
    _ROADMAPS[system] = items
    return items


# --------------------------------------------------------------------------- loading

class Ticket:
    def __init__(self, system, path):
        self.system, self.path = system, path
        self.slug = os.path.basename(path)
        self.num = self.slug.split("-", 1)[0]
        self.id = f"{system} {self.num}"
        self.state, self.state_error = {}, None
        sp = os.path.join(path, "state.json")
        if os.path.exists(sp):
            try:
                with open(sp, encoding="utf-8") as f:
                    self.state = json.load(f)
            except Exception as e:  # noqa: BLE001 - report, never crash on one bad file
                self.state_error = f"{type(e).__name__}: {e}"
        else:
            self.state_error = "no state.json"

    def get(self, *keys, default=None):
        for k in keys:
            if k in self.state and self.state[k] not in (None, "", [], {}):
                return self.state[k]
        return default

    @property
    def stage_raw(self):
        return str(self.get("current_stage", "status", default="?"))

    @property
    def triage(self):
        """One-time triage record (RAL ticket 084 S6): {"date", "decision": parked | closed-completed | closed-superseded | keep, "note", "revisit_when"}."""
        tr = self.state.get("triage")
        return tr if isinstance(tr, dict) else {}

    @property
    def closed(self):
        if str(self.triage.get("decision", "")).startswith("closed"):
            return True
        c = self.state.get("closed")
        if c is True or (isinstance(c, str) and c.strip()):
            return True
        return bool(CLOSED_RE.match(self.stage_raw)) or bool(CLOSED_RE.match(str(self.state.get("status", ""))))

    @property
    def parked(self):
        if self.triage.get("decision") == "parked":
            return not self.closed
        return not self.closed and any(PARKED_RE.search(str(self.state.get(k, ""))[:60]) for k in ("current_stage", "status"))

    @property
    def parent(self):
        """state.json.parent as "<SYSTEM> NNN" (RAL ticket 087 Q-4); None when absent or empty. The pre-v2 forms, a slug
        ("045-some-slug", in the primary system) or a path ("side/tickets/011-…", in another), are read as the same ticket."""
        p = self.state.get("parent")
        if not (isinstance(p, str) and p.strip()):
            return None
        p = p.strip()
        m = LEGACY_PARENT_RE.match(p)
        if m:
            return f"{LEGACY_ROOTS[m.group(1)] if m.group(1) else self.system} {m.group(2)}"
        return p

    @property
    def stale(self):
        import datetime
        try:
            return (datetime.date.today() - datetime.date.fromisoformat(self.updated)).days > STALE_DAYS
        except ValueError:
            return True

    @property
    def stage(self):
        """Short stage label: the leading code of a free-text stage sentence."""
        s = self.stage_raw.strip()
        if self.closed:
            return "closed"
        if self.parked:
            return "parked"
        m = re.match(r"^([A-Za-z]+(?:\s*\([^)]{0,14}\))?|rev\d+[-\w]*)", s)
        return (m.group(1) if m else s)[:16]

    @property
    def is_v2(self):
        return "awaiting_user" in self.state or str(self.get("created", "opened", default="")) >= V2_DATE

    @property
    def updated(self):
        u = self.get("updated", "opened", "created")
        if u:
            m = re.search(r"\d{4}-\d{2}-\d{2}", str(u))
            if m:
                return m.group(0)
        sp = os.path.join(self.path, "state.json")
        if os.path.exists(sp):
            import time
            return time.strftime("%Y-%m-%d", time.localtime(os.path.getmtime(sp)))
        return "?"

    @property
    def title(self):
        tp = os.path.join(self.path, "ticket.md")
        if os.path.exists(tp):
            with open(tp, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# "):
                        return TITLE_PREFIX_RE.sub("", line[2:].strip())
        return str(self.get("title", default=self.slug))

    def reviews(self):
        r = self.state.get("reviews")
        if isinstance(r, list):
            return [x for x in r if isinstance(x, dict)]
        if isinstance(r, dict):
            return [v for v in r.values() if isinstance(v, dict)] or [r]
        return []

    @property
    def blocking_open(self):
        """Open blocking findings from the latest review entry; '?' when not recorded as a number."""
        revs = self.reviews()
        for rv in reversed(revs):
            b = rv.get("blocking_open")
            if isinstance(b, int):
                return b
        b = self.state.get("blocking_open")
        if isinstance(b, int):
            return b
        if isinstance(b, list):
            return len(b)
        return "?" if revs else 0

    def awaiting(self):
        """What the user owes: v2 `awaiting_user`, plus legacy deps of kind user_gate (structured only)."""
        out = []
        a = self.state.get("awaiting_user")
        if isinstance(a, list):
            out += [str(x) for x in a]
        elif isinstance(a, str) and a.strip():
            out.append(a)
        deps = self.state.get("deps")
        if isinstance(deps, list):
            for d in deps:
                if isinstance(d, dict) and d.get("kind") == "user_gate":
                    out.append(f"user_gate on {d.get('on', '?')}: {d.get('note', '')}".strip())
        return out


def parent_problem(t, byid):
    """What is wrong with t's parent link, or "" (RAL ticket 087 S1). byid maps ticket IDs to tickets."""
    p = t.parent
    if p is None:
        return "" if t.state.get("parent") in (None, "") else f"parent is not a string: {t.state.get('parent')!r}"
    if not PARENT_RE.match(p):
        return f"parent {p!r} is not '<{SYSTEMS}> NNN'"
    if p == t.id:
        return "parent is the ticket itself"
    if p not in byid:
        return f"parent {p} does not exist"
    seen, cur = {t.id}, byid[p]
    while cur is not None:
        if cur.id in seen:
            return f"parent chain loops back to {cur.id}"
        seen.add(cur.id)
        cur = byid.get(cur.parent) if cur.parent else None
    if byid[p].closed and not t.closed and not t.parked:
        return f"parent {p} is closed while this ticket is open"
    if p != t.state["parent"].strip() and not t.closed:
        return f"write parent as {p!r}, not the older form {t.state['parent']!r}"
    return ""


def children(t, ts):
    return [c for c in ts if c.parent == t.id]


def live_sessions():
    """{name: status} of this machine's Claude sessions from `claude agents --json` (RAL ticket 087 S1), or None when
    that cannot be read. QRISPY_AGENTS_JSON=<file> replaces the call (tests). Only show, ls --tree and dashboard use it."""
    if not _AGENTS:
        import subprocess
        out = None
        try:
            fake = os.environ.get("QRISPY_AGENTS_JSON")
            if fake:
                with open(fake, encoding="utf-8") as f:
                    raw = f.read()
            else:
                raw = subprocess.run(["claude", "agents", "--json"], capture_output=True, text=True, timeout=15).stdout
            out = {}
            for s in json.loads(raw):
                st = str(s.get("status", "?"))
                if s.get("waitingFor"):
                    st += f": {s['waitingFor']}"
                out[str(s.get("name"))] = st
                if s.get("sessionId"):
                    _SESSION_IDS[str(s["sessionId"])] = str(s.get("name"))
        except Exception:  # noqa: BLE001 - no CLI, timeout or bad JSON: liveness unknown
            out = None
        _AGENTS.append(out)
    return _AGENTS[0]


def session_state(name, sid=None):
    """'name (busy)'; with the recorded session id, the session's name now: 'old-name → now new-name (idle)' (Q-17)."""
    if not name and not sid:
        return "-"
    live = live_sessions()
    if live is None:
        return f"{name or sid} (liveness unknown)"
    now = _SESSION_IDS.get(str(sid)) if sid else None
    if now and now != name:
        return f"{name or '-'} → now {now} ({live.get(now, '?')})"
    if name in live:
        return f"{name} ({live[name]})"
    return f"{name or sid} (not running" + ("; its session id is not live either)" if sid else "; no session_id recorded)")


def session_of(t):
    return session_state(t.state.get("session"), t.state.get("session_id"))


GO_KEYS = ("q", "kind", "what", "max_hours", "max_runs", "out", "until")


def go_problem(g):
    """What is wrong with one state.json.go_scopes entry (RAL ticket 087 Q-7), or ""."""
    if not isinstance(g, dict):
        return f"not an object: {g!r}"[:80]
    miss = [k for k in GO_KEYS if k not in g]
    if miss:
        return f"{g.get('q', '?')}: missing {', '.join(miss)}"
    if g["kind"] not in ("sim", "train", "other"):
        return f"{g['q']}: kind {g['kind']!r} is not sim/train/other"
    if not isinstance(g["max_hours"], (int, float)) or not isinstance(g["max_runs"], int):
        return f"{g['q']}: max_hours and max_runs must be numbers"
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(g["until"])):
        return f"{g['q']}: until must be YYYY-MM-DD"
    return ""


def go_usage(t, g, ts):
    """(hours, runs) of the jobs, in any ticket, launched with run_job.sh --go "<t.id> <q>"."""
    import datetime
    key, hours, runs = f"{t.id} {g.get('q')}", 0.0, 0
    for x in ts:
        for jj in glob.glob(os.path.join(x.path, "jobs", "*", "job.json")):
            try:
                with open(jj, encoding="utf-8") as f:
                    j = json.load(f)
            except Exception:  # noqa: BLE001
                continue
            if j.get("go") != key:
                continue
            runs += 1
            done = os.path.join(os.path.dirname(jj), "DONE.json")
            try:
                with open(done, encoding="utf-8") as f:
                    hours += json.load(f).get("duration_s", 0) / 3600
            except OSError:
                try:
                    hours += (datetime.datetime.now().astimezone() - datetime.datetime.fromisoformat(j["started"])).total_seconds() / 3600
                except (KeyError, ValueError):
                    pass
    return hours, runs


def jobs(t):
    """Jobs launched with `qrispy job run` (lib/jobs/run_job.sh) under <ticket>/jobs/<id>/ (RAL ticket 084 Q-23).
    Returns (id, status, detail) with status running | ended-unhandled | died | handled."""
    out = []
    for jj in sorted(glob.glob(os.path.join(t.path, "jobs", "*", "job.json"))):
        d = os.path.dirname(jj)
        try:
            with open(jj, encoding="utf-8") as f:
                j = json.load(f)
        except Exception:  # noqa: BLE001
            out.append((os.path.basename(d), "unreadable", "")); continue
        done = os.path.join(d, "DONE.json")
        if os.path.exists(os.path.join(d, "HANDLED.json")):
            status, detail = "handled", ""
        elif os.path.exists(done):
            with open(done, encoding="utf-8") as f:
                dj = json.load(f)
            status, detail = "ended-unhandled", f"exit {dj.get('exit_code')} at {str(dj.get('ended'))[:16]}; next: {j.get('next') or '-'}"
        else:
            pid = ""
            try:
                with open(os.path.join(d, "pid")) as f:
                    pid = f.read().strip()
            except OSError:
                pass
            alive = bool(pid) and qrispy_config.pid_alive(pid)
            status = "running" if alive else "died"
            detail = f"since {str(j.get('started'))[:16]}" + ("" if alive else "; no DONE.json, process gone")
        out.append((os.path.basename(d), status, detail))
    return out


def load(systems=None):
    out = []
    for system, root in ROOTS:
        if systems and system not in systems:
            continue
        for d in sorted(glob.glob(os.path.join(root, "[0-9][0-9][0-9]-*"))):
            if os.path.isdir(d):
                out.append(Ticket(system, d))
    return out


def resolve(key, tickets):
    key = key.strip()
    m = re.match(rf"^({SYSTEMS})?\s*-?\s*(\d{{1,3}})$", key, re.I)
    if m:
        sys_, num = (m.group(1) or "").upper(), m.group(2).zfill(3)
        hits = [t for t in tickets if t.num == num and (not sys_ or t.system == sys_)]
    else:
        hits = [t for t in tickets if key.lower() in t.slug.lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        sys.exit(f"qrispy: no ticket matches '{key}'")
    if all(t.num == hits[0].num for t in hits):
        sys.exit(f"qrispy: '{key}' is ambiguous: " + ", ".join(t.id for t in hits) + f" (prefix {CFG.names_text()})")
    sys.exit(f"qrispy: '{key}' matches {len(hits)} tickets: " + ", ".join(t.id for t in hits[:8]))


def short(s, n):
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


# --------------------------------------------------------------------------- commands

def parked_groups(ts):
    """Parked tickets grouped by their recorded revisit trigger (RAL ticket 084 S6, T-2)."""
    groups = {}
    for t in ts:
        if t.parked:
            groups.setdefault(str(t.triage.get("revisit_when") or "(다시 열 조건 없음)"), []).append(t)
    return dict(sorted(groups.items()))


def cmd_ls(args):
    if "--parked" in args:
        groups = parked_groups(load())
        print(f"{sum(len(v) for v in groups.values())} parked tickets in {len(groups)} revisit groups (state.json triage.revisit_when)")
        for k, v in groups.items():
            print(f"{k}: " + ", ".join(t.id for t in sorted(v, key=lambda t: (t.system, t.num))))
        return
    systems = next(({n} for n in CFG.names if f"--{n.lower()}" in args), None)  # --<system name in lower case>, e.g. --demo
    if "--tree" in args:
        return print_tree(load(), systems, "--all" in args)
    ts = load(systems)
    active = [t for t in ts if not t.closed and not t.parked]
    if "--all" in args:
        shown = ts
    elif "--recent" in args:
        shown = [t for t in active if not t.stale]
    else:
        shown = active
    n_wait = sum(1 for t in active if t.awaiting())
    n_stale = sum(1 for t in active if t.stale)
    print(f"{len(ts)} tickets: {len(active)} open ({len(active) - n_stale} updated in the last {STALE_DAYS} days, {n_stale} older), "
          f"{sum(t.parked for t in ts)} parked, {sum(t.closed for t in ts)} closed; {n_wait} open tickets owe the user something (qrispy inbox)")
    print(f"showing {len(shown)} ({'all' if '--all' in args else 'open, updated recently' if '--recent' in args else 'open'}); columns: id stage blocking-open user-items updated next-action")
    for t in sorted(shown, key=lambda t: t.updated, reverse=True):
        if t.state_error:
            print(f"{t.id:<10} {'?':<16} state.json: {t.state_error}")
            continue
        b = t.blocking_open
        print(f"{t.id:<10} {t.stage:<16} blk {str(b):<2} wait {len(t.awaiting()):<2} {t.updated[5:]:<5}  {short(t.get('next_action', default='?'), 90)}")


def print_tree(ts, systems=None, show_all=False):
    """Project → parent → child (RAL ticket 087 S1). Only tickets in a parent relation; a finished branch (closed parent,
    no open child) is folded unless --all."""
    byid = {t.id: t for t in ts}
    kids = {}
    for t in ts:
        if t.parent in byid:
            kids.setdefault(t.parent, []).append(t)
    roots = [t for t in ts if t.id in kids and t.parent not in byid and (not systems or t.system in systems)]
    orphans = [t for t in ts if t.parent and t.parent not in byid and (not systems or t.system in systems)]

    def open_below(t, seen=()):
        return any((not c.closed and not c.parked) or open_below(c, seen + (t.id,)) for c in kids.get(t.id, []) if c.id not in seen)

    def line(t, depth):
        st = "closed" if t.closed else "parked" if t.parked else short(t.stage_raw, 18)
        print(f"{'  ' * depth}{t.id:<10} {st:<18} session {session_of(t)}  {short(t.title, 60)}")

    def walk(t, depth, seen):
        line(t, depth)
        for c in sorted(kids.get(t.id, []), key=lambda c: c.num):
            if c.id in seen:
                print(f"{'  ' * (depth + 1)}{c.id} (loop)")
                continue
            if show_all or not c.closed or open_below(c, seen):
                walk(c, depth + 1, seen + (c.id,))
            else:
                print(f"{'  ' * (depth + 1)}{c.id:<10} closed")

    shown = [r for r in roots if show_all or not r.closed or open_below(r)]
    print(f"{len(roots)} parent tickets ({len(roots) - len(shown)} finished, folded), {sum(len(v) for v in kids.values())} child tickets"
          + (f", {len(orphans)} naming a missing parent" if orphans else "") + "; columns: id stage session title")
    for system in [s for s, _ in ROOTS if not systems or s in systems]:
        group = [r for r in shown if r.system == system]
        if group:
            rm = roadmap(system)
            print(f"{system}{' (ROADMAP.md)' if rm is not None else ''}")
            for r in sorted(group, key=lambda r: r.num):
                walk(r, 1, (r.id,))
    for o in orphans:
        print(f"  {o.id} → missing parent {o.parent}")
    reached = set()

    def mark(t):
        for c in kids.get(t.id, []):
            if c.id not in reached:
                reached.add(c.id)
                mark(c)
    for r in roots:
        reached.add(r.id)
        mark(r)
    looped = sorted(t.id for t in ts if t.parent in byid and t.id not in reached and (not systems or t.system in systems))
    if looped:
        print("  in a parent loop (no root): " + ", ".join(looped))


def cmd_show(args):
    if not args:
        sys.exit("usage: qrispy show <id>")
    t = resolve(" ".join(args), load())
    files = os.listdir(t.path)
    ys = sorted(f for f in files if re.match(r"y_slice_[\d_]+\.md$", f))
    revs = sorted((f for f in files if re.match(r"rev\d+\.md$", f)), key=lambda f: int(re.findall(r"\d+", f)[0]))
    print(f"{t.id} — {short(t.title, 100)}")
    print(f"path      {os.path.relpath(t.path, REPO)}")
    print(f"stage     {short(t.stage_raw, 110)}")
    print(f"updated   {t.updated}    v2-fields {'yes' if t.is_v2 else 'no (pre-v2 ticket)'}")
    print(f"next      {short(t.get('next_action', default='?'), 200)}")
    if t.state.get("session") or t.state.get("session_id"):
        print(f"session   {session_of(t)}  (owning agent session; message it by its name now, with SendMessage)")
    ts = load()
    if t.state.get("parent") not in (None, ""):
        prob = parent_problem(t, {x.id: x for x in ts})
        print(f"parent    {t.state.get('parent')}" + (f"  (WARN: {prob})" if prob else ""))
    kids = children(t, ts)
    if kids:
        print(f"children  {len(kids)}" + "".join(
            f"\n  - {c.id} {'closed' if c.closed else short(c.stage_raw, 18)}  session {session_of(c)}  {short(c.title, 50)}"
            for c in sorted(kids, key=lambda c: c.num)))
    aw = t.awaiting()
    print(f"user owes {len(aw)}" + "".join(f"\n  - {short(a, 140)}" for a in aw))
    rv = t.reviews()
    last = rv[-1] if rv else {}
    print(f"reviews   {len(revs)} rev files; latest entry: {short(last.get('review', '-'), 30)} verdict={short(last.get('verdict', '-'), 40)} blocking_open={t.blocking_open}")
    dr = t.state.get("drift") if isinstance(t.state.get("drift"), list) else []
    print(f"drift     {len(dr)}" + (f"; latest: {short(dr[-1].get('summary', ''), 100)}" if dr else ""))
    deps = t.state.get("deps") if isinstance(t.state.get("deps"), list) else []
    print(f"deps      " + (", ".join(f"{d.get('on')}({d.get('kind')})" for d in deps if isinstance(d, dict)) or "-"))
    import datetime
    for g in t.state.get("go_scopes") or []:  # scoped go (RAL ticket 087 Q-7)
        prob = go_problem(g)
        if prob:
            print(f"go        WARN {prob}")
            continue
        hrs, runs = go_usage(t, g, ts)
        expired = str(g["until"]) < datetime.date.today().isoformat()
        print(f"go        {g['q']} {g['kind']} {short(g['what'], 60)}: {hrs:.1f}/{g['max_hours']} h, {runs}/{g['max_runs']} runs, until {g['until']}"
              + (" (EXPIRED)" if expired else "") + (" (USED UP)" if hrs >= g["max_hours"] or runs >= g["max_runs"] else ""))
    rm, its, note = roadmap(t.system), t.state.get("roadmap_items") or [], t.state.get("roadmap_note")
    if rm is not None or its or note:
        shown = ", ".join(f"{i} ({(rm or {}).get(i, {}).get('status') or 'not in ROADMAP.md'}"
                          + (f", {', '.join((rm or {}).get(i, {}).get('owners') or [])}" if (rm or {}).get(i, {}).get('owners') else "") + ")"
                          for i in its)
        print(f"roadmap   " + (shown or (f"none: {short(note, 120)}" if note else "- (no roadmap_items or roadmap_note)")))
    print(f"files     ticket {'✓' if 'ticket.md' in files else '✗'}  q {'✓' if 'q_questions.md' in files else '✗'}  i {'✓' if 'i_design.md' in files else '✗'}  p {'✓' if 'p_plan.md' in files else '✗'}  slices {len(ys)}  z {'✓' if 'z_closeout.md' in files else '✗'}  CITE {'✓' if 'CITE.md' in files else '✗'}")
    print(f"deliver   {short(t.get('deliverable', default='-'), 120)}")
    js = jobs(t)
    if js:
        print("jobs      " + "; ".join(f"{jid} {st}" for jid, st, _ in js))


def gpu_status():
    """(state, one line) from lib/gpu_lock.py (RAL ticket 087 S2), or None when the tool is missing."""
    path = os.path.join(LIB, "gpu_lock.py")
    if not os.path.exists(path):
        return None
    import importlib.util
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("gpu_lock", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    d = mod.read()
    return mod.judge(d)[0], mod.line(d)


def away_line():
    """'user away since 23:10 until 07:00' from lib/launch.py away (RAL ticket 087 Q-16), or ""."""
    path = os.path.join(LIB, "launch.py")
    if not os.path.exists(path):
        return ""
    import importlib.util
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("agent_launch", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    d = mod.away_state()
    return (f"user away since {d['since'][11:16]}" + (f" until {d['until'][11:16]}" if d.get("until") else "")) if d else ""


def cmd_inbox(args):
    ts = [t for t in load() if not t.closed and not t.parked]
    items = [(t, a) for t in ts for a in t.awaiting()]
    alljobs = [(t, j) for t in load() for j in jobs(t)]
    for t, (jid, status, detail) in alljobs:
        if status in ("ended-unhandled", "died", "unreadable"):
            items.append((t, f"job {jid} {status.upper()}: {detail}"))
    running = [(t, j) for t, j in alljobs if j[1] == "running"]
    gpu = gpu_status()
    if gpu and gpu[0] == "ownerless":
        items.append((type("G", (), {"id": "GPU"})(), f"{gpu[1]} — delete it with qrispy lock release --force only if you say so"))
    pre_v2 = sum(1 for t in ts if not t.is_v2)
    print(f"{len(items)} user items in {len({t.id for t, _ in items})} tickets; {pre_v2} active tickets are pre-v2 (no awaiting_user field: only their user_gate deps are seen)")
    for t, a in items:
        print(f"{t.id:<10} {short(a, 150)}")
    if running:
        print(f"{len(running)} jobs still running:")
        for t, (jid, _, detail) in running:
            print(f"{t.id:<10} job {jid} running {detail}")
    if gpu:
        print(gpu[1])
    away = away_line()
    if away:
        print(away)


def cmd_cite(args):
    if not args:
        sys.exit("usage: qrispy cite <id>")
    t = resolve(" ".join(args), load())
    cp = os.path.join(t.path, "CITE.md")
    if os.path.exists(cp):
        stale = cite_staleness(t)
        if stale:
            print(f"⚠ {stale}\n")
        with open(cp, encoding="utf-8") as f:
            sys.stdout.write(f.read())
        return
    print(f"{t.id}: no CITE.md (citation boundary not written yet)")
    cs = t.get("claim_safe")
    if cs:
        print(f"state.json claim_safe: {short(cs, 400)}")
    for name in ("z_closeout.md",) + tuple(sorted((f for f in os.listdir(t.path) if re.match(r"rev\d+_response\.md$", f)), reverse=True)[:1]):
        if os.path.exists(os.path.join(t.path, name)):
            print(f"read before quoting: {os.path.relpath(os.path.join(t.path, name), REPO)}")
    print(f"stage: {short(t.stage_raw, 120)}")


# --------------------------------------------------------------------------- lint

CITE_JUDGED = re.compile(r"^- 판정: (\d{4}-\d{2}-\d{2})", re.M)


def cite_staleness(t):
    """Warn when the ticket moved after its citation boundary was judged (RAL ticket 084 Q-26).

    This is the one check the retired citation ledger did that mattered: a ticket record that moves
    after its posture was set needs a human to re-judge it. It warns; it never blocks or rewrites."""
    cp = os.path.join(t.path, "CITE.md")
    if not os.path.exists(cp):
        return None
    with open(cp, encoding="utf-8") as f:
        m = CITE_JUDGED.search(f.read(3000))
    if not m:
        return "CITE.md has no '- 판정: YYYY-MM-DD' line, so its age cannot be checked"
    upd = str(t.get("updated", default="") or "")[:10]
    if re.match(r"\d{4}-\d{2}-\d{2}$", upd) and upd > m.group(1):
        return f"ticket updated {upd} after CITE.md was judged {m.group(1)}: re-judge before quoting"
    return None


CITE_JUDGED_LINE = re.compile(r"^- 판정: (.*)$", re.M)
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def cite_addendum_gap(t):
    """Warn when a CLOSED ticket's CITE.md was changed after closure without a post_closeout entry.

    PAPER1 ticket 002 rev2 B2-1 (2026-10-18): another ticket edited closed tickets' CITE.md and left
    their own records (post_closeout, closeout notes) saying the old boundary; lesson L-019 recurred a
    third time, so the rule became this warning (user approval 2026-10-18). The latest date written on
    the '- 판정:' line counts as the change date. It warns when that date is later than both the
    ticket's 'updated' and its last post_closeout date. It warns; it never blocks or rewrites."""
    if not t.closed:
        return None
    cp = os.path.join(t.path, "CITE.md")
    if not os.path.exists(cp):
        return None
    with open(cp, encoding="utf-8") as f:
        m = CITE_JUDGED_LINE.search(f.read(4000))
    if not m:
        return None
    dates = DATE.findall(m.group(1))
    if not dates:
        return None
    latest = max(dates)
    upd = str(t.get("updated", default="") or "")[:10]
    pc = t.state.get("post_closeout") or []
    pc_dates = [str(e.get("date", ""))[:10] for e in pc if isinstance(e, dict)]
    last_pc = max([d for d in pc_dates if DATE.fullmatch(d)], default="")
    if latest > upd and latest > last_pc:
        return (f"CITE.md changed {latest} after closure (updated {upd or '?'}), last post_closeout "
                f"{last_pc or 'none'}: append a non-reopening post_closeout entry and note it in the closeout")
    return None


SENT_END = re.compile(r"[.!?:;)\]}`'\"。…>|]\s*$|다\.?\s*$|[가-힣]\)\s*$")


RESPONSE_FORMAT_SINCE = "2026-10-18"  # point-by-point response format starts with reviews registered on or after this date (PAPER1 ticket 004 rev3, RAL lesson L-019 device)


def response_format(t):
    """Check the latest revN_response.md answers every finding of revN.md with evidence (tools/review_response)."""
    revs = [f for f in os.listdir(t.path) if re.match(r"rev\d+_response\.md$", f)]
    if not revs:
        return []
    last = max(revs, key=lambda f: int(re.findall(r"\d+", f)[0]))
    n = re.findall(r"\d+", last)[0]
    review = os.path.join(t.path, f"rev{n}.md")
    date = next((e.get("date") or "" for e in (t.state.get("reviews") or []) if isinstance(e, dict) and e.get("review") == f"rev{n}.md"), "")
    if not os.path.exists(review) or date < RESPONSE_FORMAT_SINCE:
        return []
    import importlib.util
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("check_response", os.path.join(LIB, "check_response.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    with open(review, encoding="utf-8") as f:
        rv = f.read()
    with open(os.path.join(t.path, last), encoding="utf-8") as f:
        rs = f.read()
    return [(ok, f"{last}: {name}", detail) for ok, name, detail in mod.check(rv, rs)]


def review_registration(t, files):
    """Every revN_response.md is registered as the response of revN.md in state.json.reviews
    (PAPER1 ticket 003 rev2 A2-2, rev3 A3-3, rev4 A4-2: three rounds in a row; RAL lesson L-071, promoted)."""
    out = []
    for f in sorted((x for x in files if re.match(r"rev\d+_response\.md$", x)), key=lambda x: int(re.findall(r"\d+", x)[0])):
        rv = f.replace("_response", "")
        e = next((x for x in t.reviews() if x.get("review") == rv), None)
        resp = (e or {}).get("response")
        ok = isinstance(resp, str) and os.path.basename(resp) == f
        detail = "" if ok else (f"state.json.reviews has no entry for {rv}" if e is None else
                                f"the {rv} entry has response {resp!r}; set it to \"{f}\"")
        out.append((True if ok else "warn", f"{f}: registered as the response in state.json.reviews", detail))
    return out


# Cross-ticket citation field (RAL lesson L-070, promoted after PAPER1 ticket 003 rev2 B2-2, rev3 B3-1, rev4 B4-1):
# a Q item that points into another ticket's record must carry, per cited ticket, the source row, that ticket's
# CITE.md condition line and the exact definition (formula and estimator), before the user answers.
CROSS_CITE_SINCE = "2026-11-08"  # answered items dated before the device are history; unanswered items are always checked (and FAIL)
CROSS_CITE_REF = re.compile(rf"\b({CFG.names_alt(external=True)})(?: ticket)? (\d{{3}})(?:의|가|이|은|는|에서|에)?\s?`([^`\s]+\.[A-Za-z0-9]{{1,5}})`")
CROSS_CITE_PROCESS = {"ticket.md", "q_questions.md", "state.json", "p_plan.md", "ROADMAP.md", "LESSONS.md", "RECIPES.md",
                      "CLAUDE.md", "AGENTS.md", "METHOD_LOCAL.md"}  # working files that hold no numbers or definitions
CROSS_CITE_FIELD = re.compile(r"^\*\*(?:다른 티켓 인용|Cross-ticket citations?)\b[^*]*\*\*", re.M | re.I)
CROSS_CITE_NONE = re.compile(r"^\s*(?:인용 아님|not a citation)\b", re.I)
# Same-quantity claims (RAL lesson L-070 recur 4-5, PAPER1 ticket 003 rev5 B5-1, rev6 B6-1, rev7 A7-2; RAL ticket 090 Q-15):
# a citation row that says this ticket's quantity is the same as the source's must name a reproduction check, a script
# and its saved output under the citing ticket that recompute the source's value from the source's data with the
# stated definition; the output needs a line that starts with PASS (and none that starts with FAIL).
SAME_QTY = re.compile(r"(?:같은|동일한|똑같은)\s?(?:방식|양|정의|계산|식|추정량|방법|공식)"
                      r"|(?:정의|식|방식|계산|추정량) 그대로"
                      rf"|(?:\b(?:{CFG.names_alt(external=True)})(?: ticket)? \d{{3}}|출처)(?:\S*\s){{0,2}}?\S*?(?:와|과)\s?(?:같다|같음|같은|동일)"
                      r"|\b(?:same|identical)\s+(?:quantity|definition|method|computation|estimator|formula|metric)\b"
                      rf"|\b(?:same as|identical to|equivalent to)\s+(?:(?:the|that of)\s+)?(?:source\b|(?:{CFG.names_alt(external=True)})(?: ticket)? \d{{3}})", re.I)
SAME_QTY_NOT_AFTER = re.compile(r"^\s?(?:[^\s|]{0,4}?(?:이|가))?\s?(?:아니|아님|아닌|않)")  # "같은 양이 아니다": it differs
SAME_QTY_NOT_BEFORE = re.compile(r"\bnot\s+(?:the\s+)?$", re.I)       # "not the same quantity"
REPRO_SCRIPT_EXT = (".py", ".sh", ".bash", ".r", ".jl", ".m", ".js", ".ts", ".ipynb")
REPRO_PATH = re.compile(r"`([^`\s]+\.[A-Za-z0-9]{1,6})`")
CROSS_CITE_CHECK = "cross-ticket citations carry source row, condition line and definition"
SAME_QTY_CHECK = "a citation row that calls its quantity the same as the source's names a passing reproduction check"
Q_HEAD = re.compile(r"^#{2,4} Q-?\d+\b.*$", re.M)
Q_ANSWERED = re.compile(r"^(?:>\s*(?:사용자|user)[^:\n]*:[ \t]*\S|결정:|Decision:)", re.M | re.I)


def q_items(text):
    """(heading, body) for each Q item of a q_questions.md; the body runs to the next Q heading or ## section."""
    hs = list(Q_HEAD.finditer(text))
    out = []
    for k, h in enumerate(hs):
        end = hs[k + 1].start() if k + 1 < len(hs) else len(text)
        sec = re.search(r"^#{1,2} (?!Q-?\d)", text[h.end():end], re.M)
        out.append((h.group(0), text[h.start(): h.end() + sec.start() if sec else end]))
    return out


def cross_cite_rows(body):
    """Data rows of every cross-ticket citation field table in a Q item, as lists of cell strings."""
    rows = []
    for m in CROSS_CITE_FIELD.finditer(body):
        # "**다른 티켓 인용:** 없음 (…)" has no table; the next table of the item (its options) is not the field's (RAL ticket 090 S10)
        if re.match(r"[ \t]*(?:없음|none)\b", body[m.end():], re.I):
            continue
        table = []
        for line in body[m.end():].split("\n")[1:]:
            s = line.strip()
            if s.startswith("|"):
                table.append([c.strip() for c in s.strip("|").split("|")])
            elif s or table:
                break
        if len(table) >= 2 and all(re.fullmatch(r":?-+:?", c) for c in table[1]):
            table = table[2:]  # header and separator
        rows.extend(table)
    return rows


def cross_cited(t, body):
    """{ticket id: first reference} for each other ticket whose record file (not a working file) the text names."""
    cited = {}
    for m in CROSS_CITE_REF.finditer(body):
        tid = f"{m.group(1)} {m.group(2)}"
        if tid != t.id and m.group(3).split("/")[-1] not in CROSS_CITE_PROCESS:
            cited.setdefault(tid, f"{tid} `{m.group(3)}`")
    return cited


def cross_cite_problems(t, body):
    """Cited tickets of one Q item whose citation row is missing or incomplete: [(ticket id, what is missing)]."""
    cited = cross_cited(t, body)
    if not cited:
        return []
    rows = cross_cite_rows(body)
    blank = lambda c: not c or c in ("-", "—", "?", "…") or bool(re.fullmatch(r"<[^>]*>", c))
    out = []
    for tid, ref in cited.items():
        mine = [r for r in rows if re.search(rf"\b{tid.split()[0]}(?: ticket)? {tid.split()[1]}\b", r[0])]
        if any(len(r) >= 2 and CROSS_CITE_NONE.match(r[1]) for r in mine):
            continue
        if not rows and not CROSS_CITE_FIELD.search(body):
            out.append((ref, "no cross-ticket citation field"))
        elif not mine:
            out.append((ref, "no row for this ticket in the field"))
        elif not any(len(r) >= 3 and not any(blank(c) for c in r[:3]) for r in mine):
            out.append((ref, "row lacks the source row, the condition line or the definition"))
    return out


def same_qty_claim(text):
    """The first phrase of a cell that says the quantity is the same as the source's, or None."""
    for m in SAME_QTY.finditer(text):
        if SAME_QTY_NOT_AFTER.match(text[m.end():]) or SAME_QTY_NOT_BEFORE.search(text[:m.start()]):
            continue
        return m.group(0)
    return None


def repro_check(t, row):
    """'' when the row names a script and a saved output under ticket t whose text has a line starting with PASS
    (and none starting with FAIL); otherwise what is missing."""
    here = os.path.realpath(t.path)
    found, missing = {"script": [], "output": []}, []
    # the source and condition cells name the source's files; the check is in the definition or reproduction cell
    for p in dict.fromkeys(m.group(1) for c in row[2:] for m in REPRO_PATH.finditer(c)):
        kind = "script" if p.lower().endswith(REPRO_SCRIPT_EXT) else "output"
        hit = None
        for base in (t.path, REPO):
            q = os.path.realpath(os.path.join(base, p))
            if (q == here or q.startswith(here + os.sep)) and os.path.isfile(q):
                hit = q
                break
        if hit:
            found[kind].append(hit)
        else:
            missing.append(p)
    gone = f" (not found under this ticket: {', '.join(missing[:3])})" if missing else ""
    if not found["script"]:
        return "no reproduction script under this ticket" + gone
    if not found["output"]:
        return "no saved output of the reproduction script under this ticket" + gone
    verdicts = []
    for q in found["output"]:
        with open(q, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
        verdicts.append((any(re.match(r"\s*PASS\b", l) for l in lines), any(re.match(r"\s*FAIL\b", l) for l in lines),
                         os.path.relpath(q, t.path)))
    if any(fl for _, fl, _ in verdicts):
        return "the output has a FAIL line: " + ", ".join(n for _, fl, n in verdicts if fl)
    if not any(ok for ok, _, _ in verdicts):
        return "the output has no line starting with PASS: " + ", ".join(n for _, _, n in verdicts)
    return ""


def same_qty_problems(t, body):
    """(rows checked, [(row label, claim, what is missing)]) for citation rows that claim the source's quantity."""
    blank = lambda c: not c or c in ("-", "—", "?", "…") or bool(re.fullmatch(r"<[^>]*>", c))
    n, out = 0, []
    for r in cross_cite_rows(body):
        if len(r) >= 2 and CROSS_CITE_NONE.match(r[1]):
            continue
        # the condition cell (second) is a verbatim copy of the source's CITE.md line, so its words are not this row's claim
        claim = next((c for c in (same_qty_claim(x) for k, x in enumerate(r) if k != 1 and not blank(x)) if c), None)
        if not claim:
            continue
        n += 1
        why = repro_check(t, r)
        if why:
            out.append((short(r[0], 60), claim, why))
    return n, out


def cross_cite(t, files):
    """Per Q item that cites another ticket's record without a complete citation field (RAL lesson L-070): FAIL while the
    item is unanswered (the user must not read it without the field), WARN once answered (RAL ticket 090 Q-14)."""
    if "q_questions.md" not in files:
        return []
    with open(os.path.join(t.path, "q_questions.md"), encoding="utf-8") as f:
        text = f.read()
    m = re.search(r"작성:\s*(\d{4}-\d{2}-\d{2})|Written:\s*(\d{4}-\d{2}-\d{2})", text[:600])
    file_date = (m.group(1) or m.group(2)) if m else ""
    byid = None
    res, checked, same_checked = [], 0, 0
    for head, body in q_items(text):
        d = re.search(r"\d{4}-\d{2}-\d{2}", head)
        date = d.group(0) if d else file_date
        answered = bool(Q_ANSWERED.search(body))
        if answered and date < CROSS_CITE_SINCE:
            continue
        checked += bool(cross_cited(t, body))
        qid = re.search(r"Q-?\d+", head).group(0)
        n_same, same = same_qty_problems(t, body)
        same_checked += n_same
        if same:
            res.append(("warn" if answered else False, f"q_questions.md {qid}: {SAME_QTY_CHECK}",
                        ("answered; " if answered else "unanswered, so the user must not read it yet; ")
                        + "; ".join(f"row {lab!r} says {claim!r}: {why}" for lab, claim, why in same)
                        + ". Name the script and its saved output (under this ticket, e.g. `evidence/<name>.py` and "
                          "`evidence/<name>.out.txt`) in the row's 재현 판정 cell; the script recomputes the source's value from "
                          "the source's data with the stated definition and prints PASS. Without one, do not call it the same quantity"))
        probs = cross_cite_problems(t, body)
        if not probs:
            continue
        if byid is None:
            byid = {x.id: x for x in load()}
        hints = []
        for ref, why in probs:
            src = byid.get(" ".join(ref.split()[:2]))
            cond = ""
            if src and os.path.exists(os.path.join(src.path, "CITE.md")):
                with open(os.path.join(src.path, "CITE.md"), encoding="utf-8") as f:
                    c = re.search(r"^- (?:조건|Conditions?):\s*(.*)$", f.read(), re.M)
                cond = f"; its CITE.md condition: {short(c.group(1), 90)!r}" if c else "; its CITE.md has no condition line"
            elif src:
                cond = "; it has no CITE.md (ask the user before quoting it)"
            hints.append(f"{ref}: {why}{cond}")
        res.append(("warn" if answered else False, f"q_questions.md {qid}: {CROSS_CITE_CHECK}",
                    ("answered; " if answered else "unanswered, so the user must not read it yet; ") + "; ".join(hints) + ". Add the **다른 티켓 인용:** table (q_questions.md template), or a row "
                                        "'| <ticket file> | 인용 아님: <why> | — |' when nothing is quoted"))
    if checked and not any(CROSS_CITE_CHECK in r[1] for r in res):
        res.append((True, f"q_questions.md: {CROSS_CITE_CHECK}", ""))
    if same_checked and not any(SAME_QTY_CHECK in r[1] for r in res):
        res.append((True, f"q_questions.md: {SAME_QTY_CHECK}", ""))
    return res


def wrapped_lines(md_path):
    """Lines that look like a sentence broken across lines (heuristic, prose only).
    HTML comment blocks are not prose: a review's QRISPY-REVIEW-PROTOCOL / -META header is one (PAPER1 ticket 003 rev2 A2-4)."""
    hits, fence = [], False
    with open(md_path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    comment = set()  # lines of an HTML comment block that starts a line (outside code fences), opening and closing lines included
    inside = in_fence = False
    for i, l in enumerate(lines):
        s = l.strip()
        if not inside and s.startswith("```"):
            in_fence = not in_fence
        if in_fence:
            continue
        opened = not inside and s.startswith("<!--")
        if inside or opened:
            comment.add(i)
            inside = "-->" not in (s[4:] if opened else s)
    def prose(l):
        s = l.strip()
        return s and not re.match(r"^(#|[-*+] |\d+\. |>|\||```|<!--|\$\$|---+$|\*\*\*+$)", s)
    for i in range(len(lines) - 1):
        if lines[i].strip().startswith("```"):
            fence = not fence
        if fence or i in comment or i + 1 in comment:
            continue
        cur, nxt = lines[i], lines[i + 1]
        if prose(cur) and nxt.strip() and not re.match(r"^\s*(#|[-*+] |\d+\. |>|\||```|<!--|---+\s*$)", nxt) and not SENT_END.search(cur):
            hits.append(i + 1)
    return hits


def deviation_rows(body):
    """Rows (kind requirement/discovery) in the 'Deviation from design' table of a slice note."""
    m = re.search(r"^#+ .*(?:설계 대비 변경|Deviation from design).*$", body, re.M)
    if not m:
        return 0
    rest = body[m.end():]
    nxt = re.search(r"^#+ ", rest, re.M)
    section = rest[:nxt.start()] if nxt else rest
    return sum(1 for line in section.splitlines()
               if re.match(r"^\|\s*(?:요구 변경|발견|requirement|discovery)\b", line))


def lint_ticket(t):
    res = []  # (ok, check, detail)
    files = set(os.listdir(t.path))
    stage = t.stage_raw.strip()
    res.append((t.state_error is None, "state.json readable", t.state_error or ""))
    for k in ("current_stage", "next_action"):
        res.append((k in t.state or (k == "current_stage" and "status" in t.state), f"state.json has {k}", ""))
    res.append(("ticket.md" in files, "ticket.md exists", ""))
    res.append(("q_questions.md" in files, "q_questions.md exists", ""))
    if t.closed:
        z = os.path.join(t.path, "z_closeout.md")
        res.append((os.path.exists(z), "closed ticket has z_closeout.md", ""))
        if os.path.exists(z):
            with open(z, encoding="utf-8") as f:
                head = f.read(600)
            res.append(("PROVISIONAL" not in head.upper(), "closed ticket's closeout has no PROVISIONAL banner", ""))
    if "CITE.md" in files:
        stale = cite_staleness(t)
        res.append(("warn" if stale else True, "CITE.md judged after the ticket's last update", stale or ""))
        gap = cite_addendum_gap(t)
        if t.closed:
            res.append(("warn" if gap else True, "closed ticket: CITE.md changes recorded in post_closeout", gap or ""))
    if not t.is_v2:
        res.append((True, "pre-v2 ticket: v2 checks skipped", ""))
        return res
    for k in ("ticket_slug", "awaiting_user", "drift", "updated"):
        res.append((k in t.state, f"state.json has {k} (v2)", ""))
    rm = roadmap(t.system)
    if rm is not None and not t.closed and not t.parked:
        its, note = t.state.get("roadmap_items") or [], t.state.get("roadmap_note")
        if not (isinstance(its, list) and all(isinstance(i, str) for i in its)):
            res.append(("warn", "roadmap: state.json roadmap_items is a list of IDs", f"got {type(its).__name__}"))
            its = []
        line = ""
        tm = os.path.join(t.path, "ticket.md")
        if os.path.exists(tm):
            with open(tm, encoding="utf-8") as f:
                m = re.search(r"^- 받치는 항목: (.*)$", f.read(), re.M)
            line = m.group(1) if m else ""
        named = re.findall(r"\b(?:Item|Claim|Exp|Gap|Decision|Risk)-\d+[a-z]?\b", line.split("(")[0])
        if line or its:
            same = sorted(set(named)) == sorted(set(its)) or (not its and line.startswith("없음"))
            res.append(("warn" if not same else True, "roadmap: the ticket.md line and state.json roadmap_items name the same items",
                        "" if same else f"ticket.md {sorted(set(named)) or line[:40]!r} vs state.json {sorted(set(its))}"))
        res.append(("warn" if not its and not note else True, "roadmap: names the ROADMAP.md items it serves, or why none",
                    "" if its or note else "set state.json roadmap_items, or roadmap_note when it serves none"))
        unknown = [i for i in its if i not in rm]
        dropped = [i for i in its if rm.get(i, {}).get("status") == "dropped"]
        detail = "; ".join(x for x in (("not in ROADMAP.md: " + ", ".join(unknown)) if unknown else "",
                                       ("dropped: " + ", ".join(dropped)) if dropped else "") if x)
        res.append(("warn" if detail else True, "roadmap: named items exist and are not dropped", detail))
    if "parent" in t.state or any(x.parent == t.id for x in load()):  # parent and child tickets (RAL ticket 087 S1)
        ts = load()
        if "parent" in t.state:
            prob = parent_problem(t, {x.id: x for x in ts})
            res.append(("warn" if prob else True, "parent: names an existing ticket, without a loop, that is not closed while this one is open", prob))
        open_kids = [c.id for c in children(t, ts) if not c.closed and not c.parked]
        if t.closed and open_kids:
            res.append(("warn", "children: a closed ticket has no open child", ", ".join(open_kids)))
        elif children(t, ts):
            res.append((True, "children: a closed ticket has no open child", ""))
    if "go_scopes" in t.state:  # scoped go (RAL ticket 087 Q-7)
        gs = t.state.get("go_scopes")
        probs = [go_problem(g) for g in gs] if isinstance(gs, list) else ["go_scopes is not a list"]
        probs = [p for p in probs if p]
        res.append(("warn" if probs else True, "go_scopes: each scope has q, kind, what, max_hours, max_runs, out, until", "; ".join(probs)))
    size = os.path.getsize(os.path.join(t.path, "state.json"))
    res.append((size <= 8192, "state.json stays compact (≤ 8 KB; narrative belongs in the ticket files)", f"{size} bytes"))
    past_i = bool(re.match(r"^(S|P|Y|Z|closed|rev)", stage, re.I))
    past_p = bool(re.match(r"^(Y|Z|closed|rev)", stage, re.I))
    if past_i:
        res.append(("i_design.md" in files, "i_design.md exists (stage past I)", ""))
    if past_p:
        res.append(("p_plan.md" in files, "p_plan.md exists (stage past P)", ""))
    done = t.get("slices_completed", "slices_done", default=[])
    done = done if isinstance(done, list) else list(range(1, int(done) + 1)) if isinstance(done, int) else []
    ys = {f for f in files if re.match(r"y_slice_[\d_]+\.md$", f)}
    for n in done:
        has = any(re.match(rf"y_slice_(?:\d+_)?{n}(?:_\d+)?\.md$", f) or f == f"y_slice_{n}.md" for f in ys)
        res.append((has, f"slice {n} has a y_slice note", ""))
    for f in sorted(ys) + (["z_closeout.md"] if "z_closeout.md" in files else []):
        with open(os.path.join(t.path, f), encoding="utf-8") as fh:
            body = fh.read()
        res.append((bool(re.search(r"위험도 카드|Risk card", body[:1500])), f"{f} opens with a risk card", ""))
        if f.startswith("y_slice"):
            res.append((bool(re.search(r"설계 대비 변경|Deviation from design", body)), f"{f} has a deviation-from-design section", ""))
    by_slice = {}  # every drift entry needs a row in its slice note's deviation table (RAL ticket 084 rev3 R3-A1: it recurred three times)
    for e in (t.state.get("drift") or []):
        if isinstance(e, dict) and isinstance(e.get("slice"), int):
            by_slice[e["slice"]] = by_slice.get(e["slice"], 0) + 1
    for n, cnt in sorted(by_slice.items()):
        notes = [f for f in ys if re.match(rf"y_slice_(?:\d+_)?{n}(?:_\d+)?\.md$", f)]
        if not notes:
            continue
        rows = 0
        for f in notes:
            with open(os.path.join(t.path, f), encoding="utf-8") as fh:
                rows += deviation_rows(fh.read())
        res.append(("warn" if cnt > rows else True, f"slice {n}: every state.json drift entry has a row in the deviation table",
                    f"{cnt} drift entries, {rows} rows" if cnt > rows else ""))
    if not t.closed:
        res.extend(review_registration(t, files))
        res.extend(cross_cite(t, files))
        res.extend(response_format(t))
    ignore = set(t.state.get("lint_ignore") or [])
    for f in sorted(x for x in files if x.endswith(".md") and x not in ignore):
        w = wrapped_lines(os.path.join(t.path, f))
        res.append((not w, f"{f}: no sentence broken across lines", (f"suspect lines {w[:5]}" + (" …" if len(w) > 5 else "")) if w else ""))
    return res


def lint_repo():
    def nlines(p):
        p = os.path.expanduser(p)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return sum(1 for _ in f)
    mem = os.path.join(qrispy_config.claude_project_dir(REPO), "memory", "MEMORY.md")  # was a fixed Linux path (RAL ticket 089)
    checks = [("~/.claude/CLAUDE.md (global memory)", "~/.claude/CLAUDE.md", 30),
              ("CLAUDE.md (project memory)", os.path.join(REPO, "CLAUDE.md"), 80),
              ("auto-memory MEMORY.md index", mem, 40)]
    res = []
    for name, p, cap in checks:
        n = nlines(p)
        if n is None and name.startswith("~/.claude/CLAUDE.md"):  # a computer whose user keeps no personal rules (RAL ticket 090)
            res.append((True, f"{name} ≤ {cap} lines", "none"))
            continue
        res.append((n is not None and n <= cap, f"{name} ≤ {cap} lines", f"{n} lines" if n is not None else "missing"))
    # the auto-memory line names the path it checked, and a machine with no memory yet passes (RAL ticket 089 Q-7, Q-8)
    shown = "~" + mem[len(os.path.expanduser("~")):] if mem.startswith(os.path.expanduser("~") + os.sep) else mem
    n = res[-1]
    res[-1] = (True, n[1], f"none yet at {shown}") if nlines(mem) is None else (n[0], n[1], f"{n[2]} at {shown}")
    for sk in sorted(glob.glob(os.path.join(REPO, ".claude", "skills", "*", "SKILL.md")) + glob.glob(os.path.join(qrispy_config.PLUGIN, "skills", "*", "SKILL.md"))):  # + the kit's own (RAL ticket 090)
        name = ("qrispy:" if sk.startswith(qrispy_config.PLUGIN) else "") + os.path.basename(os.path.dirname(sk))
        with open(sk, encoding="utf-8") as f:
            txt = f.read()
        ok, detail = txt.startswith("---\n") and txt.count("---\n") >= 2, "no frontmatter block"
        if ok:
            try:
                import yaml  # a broken frontmatter is silently dropped by Claude Code (LESSONS RAL lesson L-011)
                fm = yaml.safe_load(txt.split("---\n", 2)[1]) or {}
                ok, detail = isinstance(fm, dict) and bool(fm.get("description")), "" if fm.get("description") else "no description"
            except ImportError:
                ok, detail = True, "pyyaml missing: not parsed"
            except Exception as e:  # noqa: BLE001
                ok, detail = False, f"YAML error: {str(e).splitlines()[0][:80]}"
        res.append((ok, f"skill {name}: frontmatter parses and has a description", detail))
    for system, root in ROOTS:  # two sessions opening tickets at once can pick the same number (RAL ticket 084 Q-31)
        nums = {}
        for d in glob.glob(os.path.join(str(root), "[0-9][0-9][0-9]-*")):
            if os.path.isdir(d):
                nums.setdefault(os.path.basename(d)[:3], []).append(os.path.basename(d))
        known = KNOWN_DUP_NUMBERS.get(system, set())
        dup = {n: v for n, v in nums.items() if len(v) > 1 and n not in known}
        detail = "; ".join(", ".join(sorted(v)) for v in dup.values()) or (f"known historic duplicates: {', '.join(sorted(known))}" if known else "")
        res.append(("warn" if dup else True, f"{system} ticket numbers are unique", detail))
    res.extend(kit_rows())
    byid = None
    for system, _ in ROOTS:  # project roadmap ledgers (RAL ticket 086)
        rm = roadmap(system)
        if rm is None:
            continue
        byid = byid or {t.id: t for t in load()}
        badst = [i for i, r in rm.items() if r["status"] is not None and r["status"] not in ROADMAP_STATUSES]
        res.append(("warn" if badst else True, f"{system} ROADMAP.md: status values are {'/'.join(ROADMAP_STATUSES)}", ", ".join(badst[:8])))
        unknown = sorted({o for r in rm.values() for o in r["owners"] if o not in byid})
        res.append(("warn" if unknown else True, f"{system} ROADMAP.md: owner tickets exist", ", ".join(unknown)))
        stale = [f"{i} ({', '.join(r['owners'])})" for i, r in rm.items()
                 if r["status"] in ("planned", "active") and r["owners"] and all(o in byid and byid[o].closed for o in r["owners"])]
        res.append(("warn" if stale else True, f"{system} ROADMAP.md: no planned/active row whose owning tickets are all closed", "; ".join(stale[:8])))
    allts = load()  # parent and child tickets (RAL ticket 087 S1)
    pmap = {t.id: t for t in allts}
    probs = [f"{t.id}: {p}" for t in allts for p in [parent_problem(t, pmap)] if p]
    res.append(("warn" if probs else True, "ticket parents exist, do not loop, and no open ticket sits under a closed parent", "; ".join(probs[:8])))
    a, c = os.path.join(REPO, "AGENTS.md"), os.path.join(REPO, "CLAUDE.md")
    # AGENTS.md is how Codex and other agents read the same instructions; `qrispy init` creates it (RAL ticket 090, user 2026-11-05)
    res.append((os.path.islink(a) and os.path.realpath(a) == os.path.realpath(c), "AGENTS.md is a symlink to CLAUDE.md (for Codex and other agents)",
                "" if os.path.lexists(a) else "missing — ln -s CLAUDE.md AGENTS.md"))
    bad = unbacked_run_claims(operating_docs())
    res.append(("warn" if bad else True, "operating docs: a line saying where something was tested names its saved output",
                "; ".join(bad[:8]) + (" — name the output file (evidence/…) on the same line, or drop the claim" if bad else "")))
    return res


def kit_rows():
    """Whether Claude Code on this computer loads the kit for this repository (RAL ticket 090 Q-10 C: the plugin is installed
    for the user but turned on by the repository's settings; the guard is a user hook from the kit clone, for every repository).
    A missing guard or plugin is a FAIL, as RAL ticket 089 Q-4 decided for the guard."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("qrispy_kit_install", os.path.join(os.path.dirname(qrispy_config.PLUGIN), "install.py"))
    inst = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inst)
    rows = {name: (ok, d) for name, ok, d in inst.check()}
    repo_s, user_s = {}, inst.read_json(os.path.join(inst.config_dir(), "settings.json"), {})
    try:
        with open(os.path.join(REPO, ".claude", "settings.json"), encoding="utf-8") as f:
            repo_s = json.load(f)
    except (OSError, ValueError):
        pass
    on_here = (repo_s.get("enabledPlugins") or {}).get(inst.PLUGIN_ID, (user_s.get("enabledPlugins") or {}).get(inst.PLUGIN_ID)) is True
    deny = rows["deny rules for destructive git commands"][0] or all(r in ((repo_s.get("permissions") or {}).get("deny") or []) for r in inst.DENY)
    need = [("marketplace", rows["marketplace qrispy-kit points at this clone"][0]), ("plugin installed", rows["plugin qrispy@qrispy-kit installed"][0]),
            ("plugin turned on for this repository (.claude/settings.json enabledPlugins)", on_here),
            ("guard hook from the kit clone", rows["guard hook registered from this clone (every repository)"][0]),
            ("deny rules (user or repository settings)", deny)]
    missing = [n for n, ok in need if not ok]
    out = [(not missing, "qrispy kit: the guard hook and deny rules are set, and Claude Code loads the plugin here (core rules, skills)",
            ("missing: " + "; ".join(missing) + f" — run python3 {os.path.join(os.path.dirname(qrispy_config.PLUGIN), 'install.py')} --install"
             + ("; and `qrispy init` here" if not on_here else "")) if missing else "")]
    for name in ("~/.local/bin/qrispy links to this clone", "no other guard registration beside this clone's", "plugin off for the user (repositories turn it on)"):
        ok, d = rows[name]
        out.append((True if ok else "warn", f"qrispy kit: {name}", d))
    return out


# A line that says where something ran ("tested on Linux", "macOS에서 9/9 통과") must name the saved output of that run
# on the same line (lesson L-040 of RAL ticket 089, broken twice and promoted to this check, RAL ticket 090).
RUN_CLAIM = re.compile(r"(?i)\b(tested|passe[sd]|runs?|ran) on (macOS|Linux|x86|aarch64|arm64|[A-Z][\w-]+ machine)"
                       r"|(macOS|Linux|aarch64|x86|기계|컴퓨터)(와 [^ ]+)?에서 (\d+/\d+ )?(시험함|시험했|통과|돌려 보았|돌렸)")
RUN_EVIDENCE = re.compile(r"evidence/|results/|\.(txt|out|log|jsonl|csv)\b")


def operating_docs():
    """The documents agents follow: READMEs under tools/ and docs/, the primary ticket root's *.md, CLAUDE.md."""
    pats = ["tools/**/README.md", "docs/**/*.md", os.path.join(CFG.primary_root, "*.md"), "CLAUDE.md"]
    return sorted({p for pat in pats for p in glob.glob(os.path.join(REPO, pat), recursive=True)})


def unbacked_run_claims(paths):
    out = []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
                if RUN_CLAIM.search(line) and not RUN_EVIDENCE.search(line):
                    out.append(f"{os.path.relpath(p, REPO)}:{i}")
    return out


def _table_opts(body):
    opts = []
    for b in body:
        if b.startswith("|"):
            cells = [c.strip() for c in b.strip().strip("|").split("|")]
            om = re.match(r"^`([^`]+)`$", cells[0]) if cells else None
            if om and len(cells) >= 2:
                desc = " | ".join(cells[1:])
                opts.append([om.group(1), om.group(1), re.sub(r"\s*\*\*\(권고\)\*\*", "", desc).strip(), 1 if "(권고)" in desc else 0])
    return opts


def _question_card(t, head, body, note="", base_title="", base_body=()):
    m = re.match(r"^(Q-\d+[a-z]?(?: \S*라운드)?)\s*(.*)$", head)
    qid, title = (m.group(1), m.group(2)) if m else (head[:20], head)
    if base_title and "라운드" in qid:  # a re-ask heading says only "(설명, date)": lead with the question it re-asks
        title = f"{base_title} — {title}".strip(" —")
    para, rec = [], ""
    opts = _table_opts(body)
    for b in body:
        rm = re.search(r"\*\*권고:\*\*\s*(.*)", b)
        if rm:
            rec = rm.group(1).strip()
            if not b.startswith("**권고:**"):
                para.append(b[:rm.start()].strip())
        elif b.strip() and not b.startswith("|") and not b.startswith(">") and len(" ".join(para)) < 600:
            para.append(b.strip())
    ctx = " ".join(p for p in para if p) or note
    if not opts and base_body:  # a re-ask that points back to the table of its first round
        opts = _table_opts(base_body)
        rmark = re.match(r"^`([^`]+)`", rec)
        if opts and rmark:
            opts = [[o[0], o[1], o[2], 1 if o[0] == rmark.group(1) else 0] for o in opts]
    if not opts:
        opts = [["as-recommended", "권고대로", short(rec, 160) if rec else "", 1], ["other", "다르게 (메모에 적기)", "", 0]]
    detail = ([["권고", rec]] if rec else []) + ([["맥락 전문", ctx]] if len(ctx) > 300 else []) + ([["state.json", note]] if note and note != ctx else [])
    return {"w": f"{t.id} — {short(t.title, 50)}", "id": f"{t.id} {qid}", "t": title or qid, "type": "radio",
            "ctx": short(ctx, 300), "detail": detail, "opts": opts}


def open_questions(t):
    """Unanswered Q items of ticket t as page cards (RAL ticket 087 Q-15). Two sources: a block that ends in an empty answer
    line ('> 사용자 답:'), from the nearest '###'/'####' heading above it; and every `awaiting_user` entry that starts
    with Q-n, as the last block headed Q-n (a re-ask such as '#### Q-1 2라운드' often has no empty answer line;
    PAPER1 ticket 003 pilot note 19)."""
    qp = os.path.join(t.path, "q_questions.md")
    if not os.path.exists(qp):
        return []
    with open(qp, encoding="utf-8") as f:
        lines = f.read().splitlines()
    heads = [k for k, ln in enumerate(lines) if re.match(r"^#{2,4} ", ln)]
    out, done = [], set()
    for i, ln in enumerate(lines):
        if not re.match(r"^> 사용자 답:\s*$", ln):
            continue
        h = next((k for k in reversed(heads) if k < i and re.match(r"^#{3,4} ", lines[k])), None)
        if h is not None:
            card = _question_card(t, re.sub(r"^#{3,4} ", "", lines[h]).strip(), lines[h + 1:i])
            out.append(card); done.add(card["id"].split(" ", 2)[2].split()[0])
    for a in t.awaiting():
        m = re.match(r"^(Q-\d+[a-z]?)\b", str(a))
        if not m or m.group(1) in done:
            continue
        qid = m.group(1)
        hs = [k for k in heads if re.match(r"^#{3,4} " + re.escape(qid) + r"\b", lines[k])]
        if not hs:
            out.append({"w": f"{t.id} — {short(t.title, 50)}", "id": f"{t.id} {qid}", "t": short(a, 120), "type": "radio", "ctx": str(a),
                        "detail": [], "opts": [["as-recommended", "권고대로", "", 1], ["other", "다르게 (메모에 적기)", "", 0]]})
        else:
            h = hs[-1]
            base = re.sub(r"^#{3} " + re.escape(qid) + r"\s*", "", lines[hs[0]]).strip() if lines[hs[0]].startswith("### ") else ""
            nxt = next((k for k in heads if k > hs[0]), len(lines))
            base_body = lines[hs[0] + 1:nxt] if h != hs[0] else ()
            end = next((k for k in heads if k > h and re.match(r"^#{2,3} ", lines[k]) or (k > h and lines[k].startswith("#### ") and not lines[k][5:].startswith(qid + " "))), len(lines))
            out.append(_question_card(t, re.sub(r"^#{3,4} ", "", lines[h]).strip(), lines[h + 1:end], note=str(a), base_title=base, base_body=base_body))
        done.add(qid)
    return out


def cmd_questions(args):
    """qrispy questions --tree <id> [--html out.html]: every open Q item of a ticket and all tickets under it on one
    decision page (the plan-page decision template). Answers are recorded by the session that receives them, verbatim,
    in each ticket's own q_questions.md (RAL ticket 087 Q-15, Q-1)."""
    if len(args) < 2 or args[0] != "--tree":
        sys.exit("usage: qrispy questions --tree <id> [--html out.html]")
    html_out = None
    if "--html" in args:
        k = args.index("--html")
        html_out = os.path.abspath(args[k + 1])
        args = args[:k] + args[k + 2:]
    ts = load()
    root = resolve(" ".join(args[1:]), ts)
    order, seen = [root], {root.id}
    for t in order:  # breadth-first over children
        for c in sorted(children(t, ts), key=lambda c: (c.system, c.num)):
            if c.id not in seen:
                seen.add(c.id); order.append(c)
    cards = [c for t in order for c in open_questions(t)]
    print(f"{len(cards)} open questions in {len({c['w'] for c in cards})} of {len(order)} tickets under {root.id}")
    for c in cards:
        print(f"  {c['id']:<22} {short(c['t'], 90)}")
    if not html_out:
        return
    tpl = os.path.join(qrispy_config.PLUGIN, "skills", "plan-page", "templates", "decision.html")
    with open(tpl, encoding="utf-8") as f:
        page = f.read()
    import datetime
    stamp = datetime.datetime.now().strftime("%m%d-%H%M")
    data = {"title": f"{root.id} 아래 열린 질문 ({len(cards)})", "ticket": root.id, "round": stamp,
            "record_to": "각 티켓의 q_questions.md (질문 ID 앞의 티켓)", "queue_key": f"questions-{root.system}{root.num}-{stamp}",
            "lead": [f"{root.id}와 그 아래 하위 티켓에서 아직 답이 없는 질문 {len(cards)}개를 한 곳에 모았습니다. 고른 답은 받은 세션이 각 티켓의 q_questions.md에 원문으로 적고 그 작업자에게 알립니다.",
                     "일부만 답해도 됩니다. 답하지 않은 질문은 다음 페이지에 다시 나옵니다."],
            "questions": cards}
    m = re.search(r'(<script type="application/json" id="page-data">\n)(.*?)(\n</script>)', page, re.S)
    page = page[:m.start(2)] + json.dumps(data, ensure_ascii=False, indent=1) + page[m.end(2):]
    page = re.sub(r"<title>.*?</title>", f"<title>{root.system} {root.num} 열린 질문</title>", page, count=1)
    os.makedirs(os.path.dirname(html_out), exist_ok=True)
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"wrote {html_out}")


def cmd_lint(args):
    res = lint_repo() if args == ["--repo"] else lint_ticket(resolve(" ".join(args), load())) if args else sys.exit("usage: qrispy lint <id> | --repo")
    bad = sum(1 for ok, _, _ in res if not ok)
    warn = sum(1 for ok, _, _ in res if ok == "warn")
    print(f"{len(res) - bad}/{len(res)} PASS" + (f" ({warn} WARN)" if warn else ""))
    for ok, check, detail in res:
        print(f"{'WARN' if ok == 'warn' else 'PASS' if ok else 'FAIL'}  {check}" + (f"  ({detail})" if detail else ""))
    sys.exit(1 if bad else 0)


# --------------------------------------------------------------------------- dashboard

DASH_CSS = """
:root{--surface:#fcfcfb;--plane:#f4f4f1;--ink:#0b0b0b;--ink-2:#52514e;--muted:#898781;--grid:#e1e0d9;--fill:#2a78d6;--fill-soft:rgba(42,120,214,.10);--good:#0ca30c;--warn:#b27a00;--crit:#d03b3b}
@media (prefers-color-scheme:dark){:root{--surface:#1a1a19;--plane:#0d0d0d;--ink:#fff;--ink-2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--fill:#3987e5;--fill-soft:rgba(57,135,229,.16);--good:#3cc23c;--warn:#fab219;--crit:#e86161}}
*,*::before,*::after{box-sizing:border-box}html,body{margin:0;background:var(--plane);color:var(--ink)}
body{font:15px/1.55 system-ui,-apple-system,"Noto Sans KR",sans-serif}main{max-width:960px;margin:0 auto;padding:24px 16px 80px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--ink-2);margin:0 0 16px}code,.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.92em}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:28px 0 10px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:8px}
.tile{background:var(--surface);border:1px solid var(--grid);border-radius:10px;padding:10px 12px}.tile b{display:block;font-size:22px}.tile span{color:var(--ink-2);font-size:13px}
.card{background:var(--surface);border:1px solid var(--grid);border-radius:12px;padding:12px 14px;margin-bottom:10px}
.card.wait{border-left:4px solid var(--warn)}.card.job{border-left:4px solid var(--crit)}
.head{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}.tid{font-weight:700;color:var(--fill);white-space:nowrap}.tt{font-weight:600;flex:1 1 240px;min-width:0}
.meta{color:var(--muted);font-size:13px}.next{color:var(--ink-2);margin:6px 0;overflow-wrap:anywhere}
ul.items{margin:6px 0;padding-left:20px}ul.items li{margin:3px 0;overflow-wrap:anywhere}
button{font:inherit;font-size:13px;cursor:pointer;border-radius:8px;border:1px solid var(--grid);background:var(--surface);color:var(--ink);padding:5px 10px}
button.done{color:#fff;background:var(--good);border-color:var(--good)}
details{margin-top:8px}summary{cursor:pointer;color:var(--muted)}
table{border-collapse:collapse;width:100%;font-size:13.5px}td{border-top:1px solid var(--grid);padding:4px 6px;vertical-align:top;overflow-wrap:anywhere}
"""

DASH_JS = """
document.addEventListener('click', e => {
  const b = e.target.closest('button[data-prompt]'); if (!b) return;
  const msg = b.dataset.prompt;
  if (window.lavish && typeof window.lavish.queuePrompt === 'function') {
    window.lavish.queuePrompt(msg, { tag: 'dashboard', text: b.dataset.label, element: b, queueKey: 'qrispy-dashboard-' + b.dataset.key });
    b.classList.add('done'); b.textContent = '대기열에 들어감 · Send로 보내기';
  } else {
    navigator.clipboard && navigator.clipboard.writeText(msg).then(() => { b.textContent = '클립보드에 복사됨'; });
  }
});
"""


def cmd_dashboard(args):
    import datetime
    import html
    if len(args) != 2 or args[0] != "--html":
        sys.exit("usage: qrispy dashboard --html <out.html>")
    out = os.path.abspath(args[1])
    esc = html.escape
    ts = load()
    active = [t for t in ts if not t.closed and not t.parked]
    recent = sorted((t for t in active if not t.stale), key=lambda t: t.updated, reverse=True)
    stale = sorted((t for t in active if t.stale), key=lambda t: t.updated, reverse=True)
    waits = [(t, t.awaiting()) for t in active if t.awaiting()]
    alljobs = [(t, j) for t in ts for j in jobs(t)]
    jobitems = [(t, j) for t, j in alljobs if j[1] in ("ended-unhandled", "died", "unreadable")]
    running = [(t, j) for t, j in alljobs if j[1] == "running"]
    gpu = gpu_status()  # RAL ticket 087: GPU lock, workers stuck at a dialog, parent → child tree
    live = live_sessions()
    by_session = {str(t.state.get("session")): t for t in active if t.state.get("session")}
    by_session.update({_SESSION_IDS[str(t.state["session_id"])]: t for t in active if str(t.state.get("session_id")) in _SESSION_IDS})
    stuck = sorted((n, st) for n, st in (live or {}).items() if "permission" in st)
    byid = {t.id: t for t in ts}
    kids = {}
    for t in ts:
        if t.parent in byid:
            kids.setdefault(t.parent, []).append(t)
    tree_roots = [t for t in ts if t.id in kids and t.parent not in byid and not t.closed]

    def btn(t, key, label, prompt):
        return f'<button data-key="{esc(key)}" data-label="{esc(label)}" data-prompt="{esc(prompt)}">{esc(label)}</button>'

    def open_btn(t):
        return btn(t, t.num + t.system, f"{t.id} 열기",
                   f"{t.id}를 이어서 진행한다. 먼저 `qrispy show {t.system} {t.num}`의 결과와 사용자에게 대기 중인 항목을 짧게 보고하고, 다음 행동을 제안하라.")

    h = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    h.append(f'<h1>QRISPY 대시보드</h1><p class="sub">생성 {now} · <code>qrispy dashboard</code>가 각 티켓의 <code>state.json</code>과 작업 기록에서 만든 읽기 전용 페이지입니다. 상태가 바뀌면 다시 생성하세요. 버튼은 에이전트에게 보낼 요청을 Lavish 대기열에 넣습니다.</p>')
    h.append('<div class="tiles">' + "".join(f'<div class="tile"><b>{n}</b><span>{esc(l)}</span></div>' for n, l in [
        (sum(len(a) for _, a in waits) + len(jobitems) + len(stuck) + (1 if gpu and gpu[0] == "ownerless" else 0), "사용자를 기다리는 항목"), (len(running), "진행 중인 작업"),
        (len(recent), f"최근 {STALE_DAYS}일 안에 움직인 열린 티켓"), (len(stale), f"{STALE_DAYS}일 넘게 멈춘 열린 티켓")]) + "</div>")
    if gpu:
        h.append(f'<p class="sub mono">{esc(gpu[1])}</p>')
    if away_line():
        h.append(f'<p class="sub mono">{esc(away_line())} — 작업자는 멈춰 있고, 일어난 일은 돌아오면 한 번에 요약됩니다.</p>')

    h.append("<h2>사용자를 기다리는 항목</h2>")
    if not waits and not jobitems and not stuck and not (gpu and gpu[0] == "ownerless"):
        h.append('<p class="sub">없음.</p>')
    for n, st in stuck:
        owner = by_session.get(n)
        h.append(f'<section class="card job"><div class="head"><span class="tid">{esc(owner.id if owner else n)}</span>'
                 f'<span class="tt">작업자 {esc(n)}: 확인 창 앞에서 멈춤</span></div><p class="next">{esc(st)} — <code>claude attach {esc(n)}</code>로 들어가 답하세요.</p></section>')
    if gpu and gpu[0] == "ownerless":
        h.append(f'<section class="card job"><div class="head"><span class="tid">GPU</span><span class="tt">주인 없는 잠금</span></div>'
                 f'<p class="next">{esc(gpu[1])} — 지울지는 사용자가 정합니다 (<code>gpu_lock.py release --force</code>).</p></section>')
    for t, items in waits:
        h.append(f'<section class="card wait"><div class="head"><span class="tid">{esc(t.id)}</span><span class="tt">{esc(short(t.title, 90))}</span>{open_btn(t)}</div>'
                 f'<ul class="items">' + "".join(f"<li>{esc(short(a, 300))}</li>" for a in items) + "</ul></section>")
    for t, (jid, st, detail) in jobitems:
        h.append(f'<section class="card job"><div class="head"><span class="tid">{esc(t.id)}</span><span class="tt">작업 {esc(jid)} — {esc(st)}</span>'
                 + btn(t, f"{t.num}-{jid}", "결과 처리 요청", f"{t.id}의 작업 {jid}이(가) {st} 상태다 ({detail}). 기록된 다음 단계를 확인해 처리하고, 끝나면 `qrispy job handled`로 표시하라.")
                 + f'</div><p class="next">{esc(detail)}</p></section>')

    if running:
        h.append("<h2>진행 중인 작업</h2>")
        for t, (jid, _, detail) in running:
            h.append(f'<section class="card"><div class="head"><span class="tid">{esc(t.id)}</span><span class="tt">작업 {esc(jid)}</span><span class="meta">{esc(detail)}</span></div></section>')

    if tree_roots:  # parent → child (RAL ticket 087)
        def node(t, seen):
            kid = "".join(node(c, seen + (c.id,)) for c in sorted(kids.get(t.id, []), key=lambda c: c.num) if c.id not in seen)
            st = "closed" if t.closed else "parked" if t.parked else t.stage
            sess = session_of(t)
            return (f'<li><span class="mono">{esc(t.id)}</span> {esc(short(t.title, 60))} <span class="meta">· {esc(short(st, 20))} · 세션 {esc(sess)}</span>'
                    + (f"<ul>{kid}</ul>" if kid else "") + "</li>")
        h.append("<h2>상위 → 하위 티켓</h2>" + "".join(f'<section class="card"><ul class="items">{node(r, (r.id,))}</ul></section>' for r in sorted(tree_roots, key=lambda r: (r.system, r.num))))

    for system, _ in ROOTS:  # roadmap ledger: which tickets serve which item (RAL ticket 086)
        rm = roadmap(system)
        if not rm:
            continue
        serving = {}
        for t in active:
            if t.system == system:
                for i in t.state.get("roadmap_items") or []:
                    serving.setdefault(i, []).append(t.id)
        h.append(f"<h2>{esc(system)} 로드맵 — 항목별 티켓</h2><table>" + "".join(
            f'<tr><td class="mono">{esc(i)}</td><td>{esc(r["status"] or "-")}</td><td class="mono">{esc(", ".join(r["owners"]) or "-")}</td>'
            f'<td class="mono">{esc(", ".join(serving.get(i, [])) or "")}</td></tr>'
            for i, r in rm.items() if r["status"] is not None) + "</table>")

    h.append(f"<h2>최근 {STALE_DAYS}일 안에 움직인 열린 티켓</h2>")
    for t in recent:
        b = t.blocking_open
        meta = f"단계 {t.stage} · 갱신 {t.updated} · blocking {b} · 대기 {len(t.awaiting())}" + (" · CITE ✓" if os.path.exists(os.path.join(t.path, "CITE.md")) else "")
        h.append(f'<section class="card"><div class="head"><span class="tid">{esc(t.id)}</span><span class="tt">{esc(short(t.title, 90))}</span>{open_btn(t)}</div>'
                 f'<div class="meta">{esc(meta)}</div><p class="next">다음: {esc(short(t.get("next_action", default="?"), 260))}</p></section>')

    groups = parked_groups(ts)
    h.append(f"<h2>보류 — 다시 열 조건별 ({sum(len(v) for v in groups.values())})</h2>")
    h.append('<table>' + "".join(f'<tr><td>{esc(k)}</td><td class="mono">{esc(", ".join(t.id for t in v))}</td></tr>' for k, v in groups.items()) + "</table>")
    h.append(f"<h2>{STALE_DAYS}일 넘게 멈춘 열린 티켓 ({len(stale)})</h2>")
    h.append('<details><summary>펼치기 — 정리(닫기·보류·재개)는 별도 정리 페이지에서 결정</summary><table>' + "".join(
        f'<tr><td class="mono">{esc(t.id)}</td><td>{esc(t.updated)}</td><td>{esc(short(t.title, 70))}</td><td>{esc(short(t.get("next_action", default="?"), 120))}</td></tr>' for t in stale) + "</table></details>")

    page = ('<!doctype html><html lang="ko" data-lavish-annotate="off"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1"><title>QRISPY 대시보드</title>'
            f"<style>{DASH_CSS}</style></head><body><main>{''.join(h)}</main><script>{DASH_JS}</script></body></html>\n")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(page)
    os.replace(tmp, out)
    print(f"wrote {out}: {sum(len(a) for _, a in waits) + len(jobitems)} user items, {len(running)} running jobs, {len(recent)} recent + {len(stale)} stale open tickets")


def main(argv):
    cmds = {"ls": cmd_ls, "show": cmd_show, "inbox": cmd_inbox, "cite": cmd_cite, "lint": cmd_lint, "dashboard": cmd_dashboard,
            "questions": cmd_questions}
    if not argv or argv[0] not in cmds:
        sys.exit(__doc__.strip())
    cmds[argv[0]](argv[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
