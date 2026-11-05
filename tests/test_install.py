#!/usr/bin/env python3
"""RAL ticket 090 Q-10 C: install.py on a scratch home (real `claude plugin` commands through CLAUDE_CONFIG_DIR; no model).
The plugin is installed but off for the user; the guard is a user hook from this clone, registered once; an older guard
registration (a copy in ~/.claude/hooks) is replaced and the copy kept; unrelated settings stay. Skipped without `claude`.
Run from the kit: python3 -I tests/test_install.py"""
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUARD_CMD = f'python3 -I "{os.path.join(KIT, "plugin", "hooks", "guard_git.py")}"'


def install(home, *extra):
    env = dict(os.environ)
    env.pop("CLAUDE_CONFIG_DIR", None)
    p = subprocess.run([sys.executable, "-I", os.path.join(KIT, "install.py"), "--home", home, *extra], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


def test_install_replaces_the_old_guard_and_leaves_the_plugin_off_for_the_user():
    if not shutil.which("claude"):
        print("note: no claude CLI on PATH; skipped")
        return
    home = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_install_"))
    try:
        os.makedirs(os.path.join(home, ".claude", "hooks"))
        old = os.path.join(home, ".claude", "hooks", "guard_git.py")
        open(old, "w").write("# an older copy\n")
        json.dump({"model": "x", "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": f"python3 -I {old}", "timeout": 10}]}]}},
                  open(os.path.join(home, ".claude", "settings.json"), "w"))
        rc, out = install(home)
        assert rc == 1 and "FAIL  plugin qrispy@qrispy-kit installed" in out and "FAIL  no other guard registration" in out, out  # check only
        rc, out = install(home, "--install")
        assert rc == 0 and "FAIL" not in out, out
        s = json.load(open(os.path.join(home, ".claude", "settings.json")))
        cmds = [h["command"] for e in s["hooks"]["PreToolUse"] for h in e["hooks"]]
        assert cmds == [GUARD_CMD] and s["enabledPlugins"]["qrispy@qrispy-kit"] is False and s["model"] == "x", s
        assert not os.path.exists(old) and glob.glob(old + ".retired-*"), os.listdir(os.path.dirname(old))
        assert glob.glob(os.path.join(home, ".claude", "settings.json.bak-*"))
        assert os.path.realpath(os.path.join(home, ".local", "bin", "qrispy")) == os.path.join(KIT, "plugin", "bin", "qrispy")
        rc, out = install(home, "--install")  # a second run changes nothing and registers the guard once
        s2 = json.load(open(os.path.join(home, ".claude", "settings.json")))
        assert rc == 0 and [h["command"] for e in s2["hooks"]["PreToolUse"] for h in e["hooks"]] == [GUARD_CMD], s2
    finally:
        shutil.rmtree(home)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)}/{len(tests)} PASS")
