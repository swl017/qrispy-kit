#!/usr/bin/env python3
"""Install or check the qrispy kit on this computer (RAL ticket 090, i_design.md §7). Run once per computer, from the
kit's clone; to update later, `git pull` in the clone and start a new session (the plugin is read from the clone in place).

    python3 install.py              check only: print what differs, change nothing (exit 1 when something is missing)
    python3 install.py --install    register the clone as a local marketplace, install the plugin but leave it off for the
                                    user (each repository turns it on in its .claude/settings.json, as `qrispy init` writes),
                                    register the clone's guard hook and the deny rules for every repository, link
                                    ~/.local/bin/qrispy, and remove an older guard registration (RAL ticket 090 Q-10 C)
    python3 install.py --home DIR   act on DIR/.claude and DIR/.local/bin instead (tests)

Settings files are backed up next to themselves (settings.json.bak-<time>) before any change.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys

KIT = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ID, MARKET = "qrispy@qrispy-kit", "qrispy-kit"
DENY = ["Bash(git checkout:*)", "Bash(git restore:*)", "Bash(git reset:*)", "Bash(git clean:*)", "Bash(git stash:*)"]
OLD_HOOK = "hooks/guard_git.py"  # the guard installed as a copy in ~/.claude before the kit (RAL ticket 084 Q-32)
GUARD = os.path.join(KIT, "plugin", "hooks", "guard_git.py")  # registered from the clone, so `git pull` updates it
GUARD_CMD = f'python3 -I "{GUARD}"'



def config_dir(home=None):
    if home:
        return os.path.join(home, ".claude")
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")


def read_json(p, default):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def bash_hooks(settings):
    return [h for e in (settings.get("hooks") or {}).get("PreToolUse", []) if e.get("matcher") == "Bash" for h in e.get("hooks", [])]


def old_hook_entries(settings):
    """Guard registrations that are not this clone's: a copy in ~/.claude/hooks, or another clone."""
    return [h for e in (settings.get("hooks") or {}).get("PreToolUse", []) for h in e.get("hooks", [])
            if "guard_git.py" in str(h.get("command", "")) and h.get("command") != GUARD_CMD]


def check(home=None):
    """[(name, ok, detail)] for this computer."""
    cfg = config_dir(home)
    s = read_json(os.path.join(cfg, "settings.json"), {})
    market = read_json(os.path.join(cfg, "plugins", "known_marketplaces.json"), {}).get(MARKET) or {}
    src = ((market.get("source") or {}).get("path") or (market.get("source") or {}).get("source") or "")
    installed = (read_json(os.path.join(cfg, "plugins", "installed_plugins.json"), {}).get("plugins") or {}).get(PLUGIN_ID)
    deny = (s.get("permissions") or {}).get("deny") or []
    link = os.path.join(home or os.path.expanduser("~"), ".local", "bin", "qrispy")
    want = os.path.join(KIT, "plugin", "bin", "qrispy")
    rows = [
        ("marketplace qrispy-kit points at this clone", bool(market) and os.path.realpath(src) == os.path.realpath(KIT),
         "" if market else "not registered"),
        ("plugin qrispy@qrispy-kit installed", bool(installed), "" if installed else "not installed"),
        ("plugin off for the user (repositories turn it on)", (s.get("enabledPlugins") or {}).get(PLUGIN_ID) is False,
         "" if (s.get("enabledPlugins") or {}).get(PLUGIN_ID) is False else "on for every repository" if (s.get("enabledPlugins") or {}).get(PLUGIN_ID) else "not set"),
        ("guard hook registered from this clone (every repository)", any(h.get("command") == GUARD_CMD for h in bash_hooks(s)), ""),
        ("deny rules for destructive git commands", all(r in deny for r in DENY), ", ".join(r for r in DENY if r not in deny)),
        ("~/.local/bin/qrispy links to this clone", os.path.realpath(link) == os.path.realpath(want), "" if os.path.lexists(link) else "missing"),
        ("no other guard registration beside this clone's", not old_hook_entries(s), "; ".join(h.get("command", "") for h in old_hook_entries(s))),
    ]
    return rows


def backup(p):
    if os.path.exists(p):
        shutil.copy2(p, f"{p}.bak-{datetime.datetime.now():%Y%m%d-%H%M%S}")


def claude(args, home):
    env = dict(os.environ)
    if home:
        env["CLAUDE_CONFIG_DIR"] = config_dir(home)
    p = subprocess.run(["claude"] + args, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
    return p.returncode, (p.stdout + p.stderr).strip()


def install(home=None):
    cfg = config_dir(home)
    done = []
    for args in (["plugin", "marketplace", "add", KIT], ["plugin", "install", PLUGIN_ID], ["plugin", "disable", PLUGIN_ID, "--scope", "user"]):
        rc, out = claude(args, home)
        done.append(f"claude {' '.join(args)}: {'ok' if rc == 0 else 'FAILED'} {out.splitlines()[-1] if out else ''}")
        if rc != 0:
            return done, False
    sp = os.path.join(cfg, "settings.json")
    s = read_json(sp, {})
    before = json.dumps(s, sort_keys=True)
    s.setdefault("enabledPlugins", {})[PLUGIN_ID] = False  # off for the user; a repository's settings turn it on (Q-10 C)
    deny = s.setdefault("permissions", {}).setdefault("deny", [])
    deny.extend(r for r in DENY if r not in deny)
    old = old_hook_entries(s)
    if old:
        for e in s["hooks"]["PreToolUse"]:
            e["hooks"] = [h for h in e.get("hooks", []) if h not in old]
        s["hooks"]["PreToolUse"] = [e for e in s["hooks"]["PreToolUse"] if e.get("hooks")]
        done.append("removed the other guard registration: " + "; ".join(h.get("command", "") for h in old))
    if not any(h.get("command") == GUARD_CMD for h in bash_hooks(s)):
        pre = s.setdefault("hooks", {}).setdefault("PreToolUse", [])
        entry = next((e for e in pre if e.get("matcher") == "Bash"), None)
        if entry is None:
            entry = {"matcher": "Bash", "hooks": []}
            pre.append(entry)
        entry.setdefault("hooks", []).append({"type": "command", "command": GUARD_CMD, "timeout": 10})
        done.append(f"registered the guard hook: {GUARD_CMD}")
    if json.dumps(s, sort_keys=True) != before:
        backup(sp)
        os.makedirs(cfg, exist_ok=True)
        with open(sp, "w", encoding="utf-8") as f:
            f.write(json.dumps(s, indent=2, ensure_ascii=False) + "\n")
        done.append(f"settings written ({sp}, backup kept)")
    copy = os.path.join(cfg, OLD_HOOK)
    if old and os.path.isfile(copy):
        os.replace(copy, copy + f".retired-{datetime.datetime.now():%Y%m%d-%H%M%S}")
        done.append(f"kept the older guard copy as {copy}.retired-<time>")
    bindir = os.path.join(home or os.path.expanduser("~"), ".local", "bin")
    link = os.path.join(bindir, "qrispy")
    os.makedirs(bindir, exist_ok=True)
    if os.path.lexists(link) and not os.path.islink(link):
        done.append(f"NOT linked: {link} exists and is not a symlink")
    else:
        if os.path.lexists(link):
            os.remove(link)
        os.symlink(os.path.join(KIT, "plugin", "bin", "qrispy"), link)
        done.append(f"linked {link}")
    return done, True


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--home")
    a = ap.parse_args(argv)
    if a.install:
        done, ok = install(a.home)
        print("\n".join(done))
        if not ok:
            return 2
    rows = check(a.home)
    for name, ok, detail in rows:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    return 0 if all(ok for _, ok, _ in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
