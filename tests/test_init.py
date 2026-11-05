#!/usr/bin/env python3
"""RAL ticket 090 T-4, T-5, T-9: from `qrispy init` in an empty git repository to a closed ticket, with no hand fix to any
file the kit wrote; `init` keeps files that exist; the repository lint FAILs until the kit is installed (scratch HOME,
real `claude plugin` commands against it; no model session). Run from the kit: python3 -I tests/test_init.py"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QRISPY = os.path.join(KIT, "plugin", "bin", "qrispy")
TPL = os.path.join(KIT, "plugin", "skills", "ticket", "templates")


def write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def sh(cwd, home, *cmd):
    env = dict(os.environ, HOME=home, QRISPY_AGENTS_JSON=os.path.join(home, "agents.json"), AGENT_LOCK_DIR=os.path.join(home, "locks"))
    for k in ("QRISPY_REPO", "CLAUDE_CONFIG_DIR"):
        env.pop(k, None)
    p = subprocess.run(list(cmd), cwd=cwd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def fill(name, **kv):
    t = open(os.path.join(TPL, name), encoding="utf-8").read()
    for k, v in kv.items():
        t = t.replace(k, v)
    return t


def snapshot(root, skip):
    out = {}
    for d, _, fs in os.walk(root):
        if ".git" in d.split(os.sep) or any(d.startswith(os.path.join(root, s)) for s in skip):
            continue
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, root)] = open(p, "rb").read() if not os.path.islink(p) else os.readlink(p).encode()
    return out


def test_t4_t9_from_init_to_a_closed_ticket():
    base = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_init_"))
    repo, home = os.path.join(base, "repo"), os.path.join(base, "home")
    os.makedirs(repo); os.makedirs(home)
    write(os.path.join(home, "agents.json"), "[]")
    try:
        subprocess.run(["git", "init", "-q", repo], check=True)
        rc, out = sh(repo, home, QRISPY, "init", "--system", "DEMO", "--scratch", os.path.join(base, "scratch"))
        assert rc == 0 and "link      AGENTS.md -> CLAUDE.md" in out, out
        kit_written = snapshot(repo, skip=[])
        # T-9 first half: nothing installed for this HOME, so the kit row FAILs
        rc, out = sh(repo, home, QRISPY, "lint", "--repo")
        kit_row = next(l for l in out.splitlines() if l.startswith(("PASS", "FAIL")) and "qrispy kit: the guard hook and deny rules are set" in l)
        assert kit_row.startswith("FAIL") and "plugin installed" in kit_row, out
        # open a ticket the way the qrispy:ticket skill does: copy the templates, fill them
        t = os.path.join(repo, "tickets", "001-first")
        write(os.path.join(t, "ticket.md"), fill("ticket.md", **{"<SYSTEM> NNN — <title>": "DEMO 001 — first", "YYYY-MM-DD": "2026-11-05"}))
        write(os.path.join(t, "q_questions.md"), fill("q_questions.md", **{"RAL NNN": "DEMO 001", "<SYSTEM> NNN": "DEMO 001", "YYYY-MM-DD": "2026-11-05"}))
        st = json.loads(fill("state.json", **{"NNN-slug": "001-first", "YYYY-MM-DD": "2026-11-05"}))
        write(os.path.join(t, "state.json"), json.dumps(st, indent=2))
        rc, out = sh(repo, home, QRISPY, "show", "DEMO 001")
        assert rc == 0 and out.startswith("DEMO 001 — first"), out
        # design and plan (the kit has no template for these two; the author writes them), a slice, a review dry run, a closeout
        write(os.path.join(t, "i_design.md"), "# DEMO 001 — I: design\n\nOne slice: write the note.\n")
        write(os.path.join(t, "p_plan.md"), "# DEMO 001 — P: plan\n\n| slice | what |\n|---|---|\n| S1 | the note |\n")
        write(os.path.join(t, "y_slice_1.md"), fill("y_slice.md", **{"<SYSTEM> NNN": "DEMO 001", "RAL NNN": "DEMO 001", "YYYY-MM-DD": "2026-11-05"}))
        st.update(current_stage="Y", slices_completed=[1], slices_total=1)
        write(os.path.join(t, "state.json"), json.dumps(st, indent=2))
        rc, out = sh(repo, home, QRISPY, "review", "start", "001-first", "1", "--dry-run")
        assert rc == 0 and "ticket tickets/001-first" in out, out
        write(os.path.join(t, "z_closeout.md"), fill("z_closeout.md", **{"<SYSTEM> NNN": "DEMO 001", "RAL NNN": "DEMO 001", "YYYY-MM-DD": "2026-11-05", "<closed | PROVISIONAL — reason>": "closed-completed"}))
        st.update(current_stage="closed", triage={"date": "2026-11-05", "decision": "closed-completed", "note": "test", "successor": None, "revisit_when": None})
        write(os.path.join(t, "state.json"), json.dumps(st, indent=2))
        rc, out = sh(repo, home, QRISPY, "ls", "--all")
        assert rc == 0 and "DEMO 001" in out and "closed" in out, out
        rc, out = sh(repo, home, QRISPY, "lint", "001")
        assert "FAIL" not in out, out
        # T-9 second half: install the kit for this HOME (real claude plugin commands), then the kit row passes
        if shutil.which("claude"):
            rc, out = sh(KIT, home, sys.executable, "-I", os.path.join(KIT, "install.py"), "--install")
            assert rc == 0, out
            rc, out = sh(repo, home, QRISPY, "lint", "--repo")
            kit_row = next(l for l in out.splitlines() if "qrispy kit: the guard hook and deny rules are set" in l)
            assert kit_row.startswith("PASS"), out
            assert not [l for l in out.splitlines() if l.startswith("FAIL")], out
        else:
            print("note: no claude CLI on PATH; the install half of T-9 was skipped")
        # no file that init wrote was changed by hand
        now = snapshot(repo, skip=["tickets/001-first"])
        changed = [p for p, b in kit_written.items() if now.get(p) != b]
        assert not changed, changed
    finally:
        shutil.rmtree(base)


def test_t5_init_keeps_existing_files():
    base = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_init_keep_"))
    try:
        subprocess.run(["git", "init", "-q", base], check=True)
        write(os.path.join(base, "CLAUDE.md"), "# mine\n")
        write(os.path.join(base, ".claude", "settings.json"), json.dumps({"model": "x", "permissions": {"allow": ["Bash(make:*)"]}}))
        rc, out = sh(base, base, QRISPY, "init", "--system", "MINE")
        assert rc == 0 and "kept      CLAUDE.md (exists)" in out, out
        assert open(os.path.join(base, "CLAUDE.md")).read() == "# mine\n"
        s = json.load(open(os.path.join(base, ".claude", "settings.json")))
        assert s["model"] == "x" and "Bash(make:*)" in s["permissions"]["allow"] and s["enabledPlugins"]["qrispy@qrispy-kit"] is True, s
        assert "Bash(git stash:*)" in s["permissions"]["deny"], s
        rc, out = sh(base, base, QRISPY, "init", "--system", "MINE")
        assert "kept      .claude/settings.json (already set)" in out and "kept      qrispy.json (exists)" in out, out
    finally:
        shutil.rmtree(base)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)}/{len(tests)} PASS")
