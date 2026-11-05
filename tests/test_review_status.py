#!/usr/bin/env python3
"""RAL ticket 090 T-10 (review part) on a real freeze/record cycle in a scratch git repository:
- the working-tree status files are compared in one fixed order (LC_ALL=C), so a reordered list is not a change
  (RAL ticket 089 rev3 saw Korean file names in another order and called it a change);
- a real change in the working tree is still reported;
- the protocol block's `method/…` keys are hashed from the kit's plugin and `AGENTS.md` from the repository;
  a wrong hash refuses the round (exit 6).
Run from the kit: python3 -I tests/test_review_status.py"""
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QRISPY = os.path.join(KIT, "plugin", "bin", "qrispy")
METHOD = os.path.join(KIT, "plugin", "method")


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def repo():
    r = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_review_status_"))
    write(os.path.join(r, "qrispy.json"), json.dumps({"systems": [{"name": "DEMO", "root": "tickets"}], "review_scratch": r + "_scratch"}))
    write(os.path.join(r, "CLAUDE.md"), "# demo\n")
    os.symlink("CLAUDE.md", os.path.join(r, "AGENTS.md"))  # what Codex and other agents read
    write(os.path.join(r, "tickets", "METHOD.md"), "# local\n")
    write(os.path.join(r, "tickets", "001-a", "ticket.md"), "# DEMO 001 — a\n")
    write(os.path.join(r, "tickets", "001-a", "state.json"), json.dumps({"ticket_slug": "001-a", "current_stage": "Y"}))
    for n in ("가나.md", "Zeta.md", "alpha.md", "다라.md", "Beta.md"):  # mixed scripts and cases: locale orders differ
        write(os.path.join(r, "notes", n), n + "\n")
    subprocess.run(["git", "init", "-q", r], check=True)
    return r


def q(r, *args):
    env = dict(os.environ)
    env.pop("QRISPY_REPO", None)
    p = subprocess.run([QRISPY, *args], cwd=r, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def review_text(r, qrispy_hash=None):
    head = ("<!-- QRISPY-REVIEW-PROTOCOL\n"
            f"method/QRISPY_METHOD.md: {qrispy_hash or sha(os.path.join(METHOD, 'QRISPY_METHOD.md'))}\n"
            f"method/DEV_REVIEW_RECIPE.md: {sha(os.path.join(METHOD, 'DEV_REVIEW_RECIPE.md'))}\n"
            f"AGENTS.md: {sha(os.path.join(r, 'AGENTS.md'))}\n-->\n"
            "<!-- QRISPY-REVIEW-META\nverdict: MAY_CLOSE\nblocking_open: 0\nadvisory_open: 0\n-->\n\n# review\n\n")
    return head + "".join(f"Finding text line {i}: the slice note and the code agree on this point.\n" for i in range(80))


def test_reordered_status_is_not_a_change_and_kit_paths_attest():
    r = repo()
    try:
        rc, out = q(r, "review", "freeze", "001-a", "1")
        assert rc == 0 and "frozen" in out, out
        sb = os.path.join(r + "_scratch", "001-a", "rev1", "status_before.txt")
        lines = open(sb, encoding="utf-8").read().splitlines()
        assert len(lines) >= 5, lines
        write(sb, "\n".join(reversed(lines)) + "\n")  # as another locale's sort might have left it
        txt = os.path.join(r + "_text", "review.md")  # outside the repository: no real change to its status
        write(txt, review_text(r))
        rc, out = q(r, "review", "record", "001-a", "1", txt)
        assert rc == 0 and "NOTE: git working-tree status changed" not in out, out
        assert os.path.exists(os.path.join(r, "tickets", "001-a", "rev1.md")), out
    finally:
        shutil.rmtree(r)
        shutil.rmtree(r + "_scratch", ignore_errors=True)
        shutil.rmtree(r + "_text", ignore_errors=True)


def test_a_real_status_change_is_still_reported():
    r = repo()
    try:
        assert q(r, "review", "freeze", "001-a", "1")[0] == 0
        write(os.path.join(r, "notes", "new_during_round.md"), "x\n")
        txt = os.path.join(r, "review.md")  # itself a new untracked file, too
        write(txt, review_text(r))
        rc, out = q(r, "review", "record", "001-a", "1", txt)
        assert rc == 0 and "NOTE: git working-tree status changed" in out and "new_during_round.md" in out, out
    finally:
        shutil.rmtree(r)
        shutil.rmtree(r + "_scratch", ignore_errors=True)


def test_a_wrong_method_hash_refuses_the_round():
    r = repo()
    try:
        assert q(r, "review", "freeze", "001-a", "1")[0] == 0
        txt = os.path.join(r, "review.md")
        write(txt, review_text(r, qrispy_hash="0" * 64))
        rc, out = q(r, "review", "record", "001-a", "1", txt)
        assert rc == 6 and "method/QRISPY_METHOD.md" in out and "method/DEV_REVIEW_RECIPE.md" not in out, (rc, out)
    finally:
        shutil.rmtree(r)
        shutil.rmtree(r + "_scratch", ignore_errors=True)


def test_a_missing_protocol_entry_refuses_the_round():
    r = repo()
    try:
        assert q(r, "review", "freeze", "001-a", "1")[0] == 0
        txt = os.path.join(r + "_text", "review.md")
        write(txt, "\n".join(l for l in review_text(r).split("\n") if not l.startswith("AGENTS.md:")))
        rc, out = q(r, "review", "record", "001-a", "1", txt)
        assert rc == 6 and "AGENTS.md(missing)" in out, (rc, out)
    finally:
        shutil.rmtree(r)
        shutil.rmtree(r + "_scratch", ignore_errors=True)
        shutil.rmtree(r + "_text", ignore_errors=True)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)}/{len(tests)} PASS")
