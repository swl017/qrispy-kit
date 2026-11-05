#!/usr/bin/env python3
"""Help and usage text carries no ticket references: it is printed in every repository that installs the kit (RAL ticket 090
rev2 A2-6). Runs each help and usage path of `qrispy` and fails on "<SYSTEM> ticket NNN" or on a lesson ID (a bare "<SYSTEM> NNN" in code is caught by the kit's code scan).
Run from the kit: python3 -I tests/test_help_text.py"""
import os
import re
import subprocess
import tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QRISPY = os.path.join(KIT, "plugin", "bin", "qrispy")
REF = re.compile(r"\b[A-Z][A-Z0-9]* ticket \d{3}\b|\bL-\d{3}\b")  # a reference in kit text has the full form; example IDs ("DEMO 084") are fine
CALLS = [["--help"], ["help"], ["nonsense-subcommand"], ["lock", "--help"], ["worker", "--help"], ["init", "--help"], ["config"],
         ["check-response"], ["review"], ["job"], ["job", "run"], ["job", "wait"], ["job", "status"], ["rules"]]


def test_no_ticket_reference_in_help_or_usage():
    repo = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_help_"))
    open(os.path.join(repo, "qrispy.json"), "w").write('{"systems": [{"name": "DEMO", "root": "tickets"}], "review_scratch": "/tmp/x"}')
    env = dict(os.environ)
    env.pop("QRISPY_REPO", None)
    bad = []
    for args in CALLS:
        p = subprocess.run([QRISPY, *args], cwd=repo, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        out = p.stdout + p.stderr
        for line in out.splitlines():
            if REF.search(line):
                bad.append(f"qrispy {' '.join(args)}: {line.strip()[:120]}")
    os.remove(os.path.join(repo, "qrispy.json"))
    os.rmdir(repo)
    assert not bad, "\n".join(bad)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)}/{len(tests)} PASS")
