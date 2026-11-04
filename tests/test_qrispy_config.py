#!/usr/bin/env python3
"""Tests for qrispy_config.py and the tools that read qrispy.json (RAL ticket 089 T-3–T-7, RAL ticket 090 T-1).
Run from the kit: python3 -I tests/test_qrispy_config.py

The tools live in the kit and find the repository from the working folder (RAL 090). T-3 builds a scratch repository
whose qrispy.json names other systems (DEMO, SIDE) and other folders, holds no tools at all, and runs the kit's
`qrispy` command there: if a tool still carried a fixed system or looked for itself inside the repository, it would fail."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(KIT, "plugin", "lib")
QRISPY = os.path.join(KIT, "plugin", "bin", "qrispy")
sys.path.insert(0, LIB)
import qrispy_config as qc  # noqa: E402

DEMO = {"systems": [{"name": "DEMO", "root": "work/tickets"}, {"name": "SIDE", "root": "side/tickets"}],
        "external_systems": [{"name": "OTHER", "root": "~/nowhere-qrispy-test/tickets"}],
        "known_duplicate_numbers": {}, "review_scratch": "/tmp/qrispy-review-test"}


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def ticket(repo, root, slug, title, state):
    d = os.path.join(repo, root, slug)
    write(os.path.join(d, "ticket.md"), f"# {title}\n")
    write(os.path.join(d, "state.json"), json.dumps(dict({"ticket_slug": slug, "current_stage": "Q", "updated": "2026-11-01"}, **state)))


def demo_repo():
    r = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_config_test_"))  # realpath: macOS /var is /private/var
    write(os.path.join(r, "qrispy.json"), json.dumps(DEMO))
    write(os.path.join(r, "work", "tickets", "METHOD.md"), "# method\n")
    ticket(r, "work/tickets", "001-alpha", "DEMO 001 — alpha", {})
    ticket(r, "work/tickets", "002-beta", "DEMO 002 — beta", {"parent": "DEMO 001"})
    ticket(r, "side/tickets", "001-gamma", "SIDE 001 — gamma", {})
    write(os.path.join(r, "agents.json"), "[]")
    return r


def env_for(repo, **extra):
    e = dict(os.environ, QRISPY_AGENTS_JSON=os.path.join(repo, "agents.json"), AGENT_LOCK_DIR=os.path.join(repo, "locks"), **extra)
    if "QRISPY_REPO" not in extra:
        e.pop("QRISPY_REPO", None)
    return e


def run(repo, *cmd, cwd=None, **extra):
    p = subprocess.run(list(cmd), cwd=cwd or repo, capture_output=True, text=True, env=env_for(repo, **extra))
    return p.returncode, p.stdout + p.stderr


def test_t1_repository_is_found_from_the_working_folder():
    """RAL 090 T-1: a subfolder finds the qrispy.json above it; none above stops with the reason; QRISPY_REPO wins."""
    r = demo_repo()
    other = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_no_repo_"))
    try:
        deep = os.path.join(r, "work", "tickets", "001-alpha")
        rc, out = run(r, QRISPY, "config", "repo", cwd=deep)
        assert rc == 0 and out.strip() == r, out
        rc, out = run(r, QRISPY, "show", "DEMO 002", cwd=deep)
        assert rc == 0 and out.startswith("DEMO 002 — beta\n"), out
        rc, out = run(r, QRISPY, "ls", cwd=other)
        assert rc != 0 and f"no qrispy.json in {other} or any parent folder" in out and "Traceback" not in out, out
        rc, out = run(r, QRISPY, "config", "repo", cwd=other, QRISPY_REPO=r)
        assert rc == 0 and out.strip() == r, out
        assert qc.find_repo(deep) == r
    finally:
        shutil.rmtree(r)
        shutil.rmtree(other)


def test_t3_tools_follow_the_config():
    r = demo_repo()
    try:
        rc, out = run(r, QRISPY, "ls", "--all")
        assert rc == 0 and "DEMO 001" in out and "DEMO 002" in out and "SIDE 001" in out, out
        rc, out = run(r, QRISPY, "ls", "--all", "--side")
        assert rc == 0 and "SIDE 001" in out and "DEMO 001" not in out, out
        rc, out = run(r, QRISPY, "show", "DEMO 002")
        assert rc == 0 and out.startswith("DEMO 002 — beta\n") and "DEMO 001" in out, out  # title prefix stripped; parent resolved
        rc, out = run(r, QRISPY, "show", "001")
        assert rc == 1 and "prefix DEMO or SIDE" in out, out
        rc, out = run(r, QRISPY, "lint", "--repo")
        assert "DEMO ticket numbers are unique" in out and "SIDE ticket numbers are unique" in out and "RAL" not in out, out
        assert "PASS  ticket parents exist" in out, out
        rc, out = run(r, QRISPY, "worker", "prompt", "--ticket", "SIDE 001", "--parent", "DEMO 001",
                      "--parent-session", "s0", "--agent", "claude", "--task", "t")
        assert rc == 0 and "side/tickets/001-gamma" in out, out
        rc, out = run(r, QRISPY, "worker", "prompt", "--ticket", "RAL 001", "--parent", "DEMO 001",
                      "--parent-session", "s0", "--agent", "claude", "--task", "t")
        assert rc == 1 and "<DEMO|SIDE> NNN" in out and "Traceback" not in out, out
        rc, out = run(r, QRISPY, "review", "start", "001-alpha", "1", "--dry-run")
        assert rc == 0 and "ticket work/tickets/001-alpha" in out and "scratch /tmp/qrispy-review-test/001-alpha/rev1" in out, out
        assert "files to freeze: " in out and out.split("files to freeze:")[1].split()[0] == "3", out  # 2 ticket files + METHOD.md
        rc, out = run(r, QRISPY, "review", "start", "side/tickets/001-gamma", "1", "--dry-run")
        assert rc == 0 and "ticket side/tickets/001-gamma" in out, out
        rc, out = run(r, QRISPY, "review", "start", "work/tickets/001-alpha", "1", "--dry-run")
        assert rc != 0 and "not a ticket slug of DEMO" in out, out  # a primary ticket goes by its slug only
        os.remove(os.path.join(r, "qrispy.json"))  # RAL 089 rev1 A1-3: the reason reaches the user, not "bad slug"
        rc, out = run(r, QRISPY, "review", "start", "001-alpha", "1", "--dry-run")
        assert rc != 0 and "no qrispy.json" in out, out
        rc, out = run(r, QRISPY, "ls")
        assert rc != 0 and "no qrispy.json" in out, out
    finally:
        shutil.rmtree(r)


def test_t4_claude_project_dir():
    base = os.path.expanduser("~/.claude/projects")
    assert qc.claude_project_dir("/Users/sw/Code/2026-RAL-Active-Coop-for-Interception") == \
        os.path.join(base, "-Users-sw-Code-2026-RAL-Active-Coop-for-Interception")
    # the value RAL ticket 089 found fixed in qrispy.py, from the Linux work machine
    assert qc.claude_project_dir("/home/usrg/IsaacPX4/2026-RAL-Active-Coop-for-Interception") == \
        os.path.join(base, "-home-usrg-IsaacPX4-2026-RAL-Active-Coop-for-Interception")


def bad(text):
    d = tempfile.mkdtemp(prefix="qrispy_config_bad_")
    try:
        if text is not None:
            write(os.path.join(d, "qrispy.json"), text)
        try:
            qc.load(d)
        except qc.ConfigError as e:
            return str(e)
        return None
    finally:
        shutil.rmtree(d)


def test_t5_bad_configs_stop_with_a_reason():
    sysj = lambda systems: json.dumps({"systems": systems, "review_scratch": "/tmp/x"})  # noqa: E731
    cases = {
        "no file": (None, "no qrispy.json"),
        "not JSON": ("{", "not valid JSON"),
        "empty systems": (sysj([]), "non-empty list"),
        "duplicate name": (sysj([{"name": "A", "root": "a"}, {"name": "A", "root": "b"}]), "appears twice"),
        "duplicate root": (sysj([{"name": "A", "root": "a"}, {"name": "B", "root": "a"}]), "appears twice"),
        "lower-case name": (sysj([{"name": "ral", "root": "a"}]), "must match"),
        "absolute root": (sysj([{"name": "A", "root": "/abs/tickets"}]), "relative path"),
        "root leaving the repo": (sysj([{"name": "A", "root": "../x/tickets"}]), "relative path"),
        "no root": (sysj([{"name": "A"}]), "has no root"),
        "no review_scratch": (json.dumps({"systems": [{"name": "A", "root": "a"}]}), "'review_scratch'"),  # RAL 089 rev1 A1-3
    }
    for name, (text, want) in cases.items():
        got = bad(text)
        assert got and want in got, (name, got)
    rc = subprocess.run(["python3", "-B", os.path.join(LIB, "qrispy_config.py"), "primary-root"], capture_output=True, text=True,
                        env=dict(os.environ, QRISPY_REPO=tempfile.gettempdir()))
    assert rc.returncode != 0 and "no qrispy.json" in rc.stderr, rc


def test_t6_system_of_dir_longest_root_first():
    r = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_config_t6_"))
    try:
        write(os.path.join(r, "qrispy.json"), json.dumps({"systems": [{"name": "MAIN", "root": "tickets"}, {"name": "SUB", "root": "sub/tickets"},
                                                                       {"name": "FAR", "root": "far/away/tickets"}], "review_scratch": "/tmp/x"}))
        cfg = qc.load(r)
        assert cfg.system_of_dir(os.path.join(r, "sub", "tickets")) == "SUB"  # also ends in 'tickets'
        assert cfg.system_of_dir(os.path.join(r, "tickets")) == "MAIN"
        assert cfg.system_of_dir("/somewhere/else") is None
        os.environ.pop("QRISPY_REPO", None)
        import gpu_lock
        assert gpu_lock.from_job(os.path.join(r, "sub/tickets/017-x/jobs/j"))[0] == "SUB 017"
        assert gpu_lock.from_job(os.path.join(r, "far/away/tickets/006-x/jobs/j"))[0] == "FAR 006"
        assert gpu_lock.from_job(os.path.join(r, "elsewhere/042-x/jobs/j"))[0] == "MAIN 042"  # no match: the primary system, as before
    finally:
        shutil.rmtree(r)


def test_t7_auto_memory_line_names_its_path_and_passes_when_none_yet():
    """RAL 089 Q-7 A, Q-8: the lint line shows the path it checked; no index yet is a PASS; over 40 lines is a FAIL."""
    r = demo_repo()
    home = tempfile.mkdtemp(prefix="qrispy_config_home_")
    try:
        mem_dir = os.path.join(qc.claude_project_dir(r).replace(os.path.expanduser("~"), home, 1), "memory")
        line = lambda: next(l for l in run(r, QRISPY, "lint", "--repo", HOME=home)[1].splitlines() if "auto-memory" in l)  # noqa: E731
        shown = "~" + mem_dir[len(home):]
        got = line()
        assert got.startswith("PASS") and f"none yet at {shown}/MEMORY.md" in got, got
        os.makedirs(mem_dir)
        write(os.path.join(mem_dir, "MEMORY.md"), "x\n" * 41)
        got = line()
        assert got.startswith("FAIL") and f"41 lines at {shown}/MEMORY.md" in got, got
        write(os.path.join(mem_dir, "MEMORY.md"), "x\n" * 3)
        got = line()
        assert got.startswith("PASS") and "3 lines at" in got, got
    finally:
        shutil.rmtree(r)
        shutil.rmtree(home)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)}/{len(tests)} PASS")
