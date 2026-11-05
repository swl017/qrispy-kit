#!/usr/bin/env python3
"""RAL ticket 090 T-10 (lint part): `qrispy lint --repo` warns on an operating-doc line that says where something was
tested without naming the saved output (lesson L-040 of RAL ticket 089, promoted), and that AGENTS.md is a symlink to CLAUDE.md.
Run from the kit: python3 -I tests/test_lint_evidence.py"""
import json
import os
import shutil
import subprocess
import tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QRISPY = os.path.join(KIT, "plugin", "bin", "qrispy")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def lint(repo):
    env = dict(os.environ, QRISPY_AGENTS_JSON=os.path.join(repo, "agents.json"))
    env.pop("QRISPY_REPO", None)
    p = subprocess.run([QRISPY, "lint", "--repo"], cwd=repo, capture_output=True, text=True, env=env)
    return p.stdout + p.stderr


def row(out, name):
    return next((l for l in out.splitlines() if name in l), None)


def test_unbacked_claim_warns_and_backed_claim_passes():
    r = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_lint_ev_"))
    try:
        write(os.path.join(r, "qrispy.json"), json.dumps({"systems": [{"name": "DEMO", "root": "tickets"}], "review_scratch": "/tmp/x"}))
        write(os.path.join(r, "agents.json"), "[]")
        write(os.path.join(r, "tickets", "001-a", "state.json"), json.dumps({"ticket_slug": "001-a", "current_stage": "Q"}))
        write(os.path.join(r, "tickets", "001-a", "ticket.md"), "# DEMO 001 — a\n")
        write(os.path.join(r, "docs", "guide.md"), "The job tools are tested on Linux and macOS.\n")
        out = lint(r)
        got = row(out, "operating docs: a line saying where something was tested")
        assert got and got.startswith("WARN") and "docs/guide.md:1" in got, out
        got = row(out, "AGENTS.md is a symlink")
        assert got and got.startswith("FAIL") and "ln -s CLAUDE.md AGENTS.md" in got, out  # other agents read AGENTS.md
        write(os.path.join(r, "CLAUDE.md"), "# demo\n")
        os.symlink("CLAUDE.md", os.path.join(r, "AGENTS.md"))
        assert row(lint(r), "AGENTS.md is a symlink").startswith("PASS")
        write(os.path.join(r, "docs", "guide.md"), "The job tools are tested on Linux (`evidence/jobs_linux.txt`).\n"
                                                 "작업 도구는 macOS에서 9/9 통과 (`tests/runs/macos.txt`).\n")
        got = row(lint(r), "operating docs: a line saying where something was tested")
        assert got and got.startswith("PASS"), got
        write(os.path.join(r, "tools", "x", "README.md"), "작업 도구는 macOS에서 9/9 통과.\n")
        got = row(lint(r), "operating docs: a line saying where something was tested")
        assert got and got.startswith("WARN") and "tools/x/README.md:1" in got, got
    finally:
        shutil.rmtree(r)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)}/{len(tests)} PASS")
