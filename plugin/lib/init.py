#!/usr/bin/env python3
"""qrispy init — set up a repository for the qrispy kit.

    qrispy init --system NAME [--root tickets] [--scratch /tmp/qrispy-review] [--dry-run]

Run it in the repository's root folder. It writes, and never overwrites (an existing file is reported "kept"):
  qrispy.json                 one ticket system NAME with its folder
  <root>/LESSONS.md           the mistake ledger, header only
  <root>/METHOD_LOCAL.md      the repository's own rules, empty sections
  CLAUDE.md                   a short skeleton, only when there is none
  AGENTS.md                   a symlink to CLAUDE.md, for Codex and other agents, only when there is none
  .claude/settings.json       merged, other keys kept: the plugin enabled (qrispy@qrispy-kit), the deny rules for
                              destructive git commands, read-only qrispy commands allowed, background agents not isolated
                              in worktrees (worktree.bgIsolation none, as the method's Orchestration section assumes)
"""
# Provenance (kept out of the help text, which every repository prints): RAL ticket 090, i_design.md §6.
import argparse
import json
import os
import re
import sys

KIT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATES = os.path.join(KIT, "templates", "repo")
PLUGIN_ID = "qrispy@qrispy-kit"
DENY = ["Bash(git checkout:*)", "Bash(git restore:*)", "Bash(git reset:*)", "Bash(git clean:*)", "Bash(git stash:*)"]
ALLOW = [f"Bash(qrispy {c}:*)" for c in ("ls", "show", "inbox", "cite", "lint", "config")] + ["Bash(qrispy rules)"]


def write_new(path, text, report, dry):
    if os.path.lexists(path):
        report.append(f"kept      {path} (exists)")
        return
    report.append(f"write     {path}")
    if not dry:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)


def merged_settings(old):
    s = json.loads(json.dumps(old))  # a copy
    s.setdefault("enabledPlugins", {})[PLUGIN_ID] = True
    perms = s.setdefault("permissions", {})
    for key, rules in (("deny", DENY), ("allow", ALLOW)):
        have = perms.setdefault(key, [])
        have.extend(r for r in rules if r not in have)
    s.setdefault("worktree", {}).setdefault("bgIsolation", "none")
    return s


def main(argv):
    ap = argparse.ArgumentParser(prog="qrispy init", description=__doc__.split("\n\n")[0])
    ap.add_argument("--system", required=True, help="ticket system name, e.g. ABC (capitals and digits)")
    ap.add_argument("--root", default="tickets", help="ticket folder relative to the repository (default: tickets)")
    ap.add_argument("--scratch", default="/tmp/qrispy-review", help="parent folder of review-round scratch folders")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not re.match(r"^[A-Z][A-Z0-9]*$", a.system):
        sys.exit(f"qrispy init: --system {a.system!r} must be capitals and digits, starting with a capital")
    root = a.root.strip("/")
    if os.path.isabs(root) or ".." in root.split("/"):
        sys.exit(f"qrispy init: --root {a.root!r} must be a folder inside the repository")
    if not os.path.isdir(".git"):
        print("qrispy init: note: no .git here; run this in the repository's root folder", file=sys.stderr)
    rep, dry = [], a.dry_run
    cfg = {"systems": [{"name": a.system, "root": root}], "external_systems": [], "known_duplicate_numbers": {}, "review_scratch": a.scratch}
    write_new("qrispy.json", json.dumps(cfg, indent=2) + "\n", rep, dry)
    for name in ("LESSONS.md", "METHOD_LOCAL.md"):
        with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
            write_new(os.path.join(root, name), f.read(), rep, dry)
    with open(os.path.join(TEMPLATES, "CLAUDE.md"), encoding="utf-8") as f:
        write_new("CLAUDE.md", f.read().replace("{root}", root).replace("{system}", a.system), rep, dry)
    if os.path.lexists("AGENTS.md"):
        ok = os.path.islink("AGENTS.md") and os.path.realpath("AGENTS.md") == os.path.realpath("CLAUDE.md")
        rep.append(f"kept      AGENTS.md ({'a symlink to CLAUDE.md' if ok else 'exists but is not a symlink to CLAUDE.md: qrispy lint --repo will FAIL'})")
    else:
        rep.append("link      AGENTS.md -> CLAUDE.md")
        if not dry:
            os.symlink("CLAUDE.md", "AGENTS.md")
    sp = os.path.join(".claude", "settings.json")
    try:
        with open(sp, encoding="utf-8") as f:
            old = json.load(f)
    except FileNotFoundError:
        old = {}
    except ValueError as e:
        sys.exit(f"qrispy init: {sp} is not valid JSON ({e}); fix it first")
    new = merged_settings(old)
    if new == old:
        rep.append(f"kept      {sp} (already set)")
    else:
        rep.append(f"merge     {sp} (plugin {PLUGIN_ID}, {len(DENY)} deny rules, read-only qrispy commands, worktree.bgIsolation)")
        if not dry:
            os.makedirs(".claude", exist_ok=True)
            with open(sp, "w", encoding="utf-8") as f:
                f.write(json.dumps(new, indent=2, ensure_ascii=False) + "\n")
    print(("# dry run: nothing written\n" if dry else "") + "\n".join(rep))
    print(f"next: open a first ticket with the qrispy:ticket skill, or `mkdir {root}/{a.system}-001-<slug>`; check with `qrispy lint --repo`")


if __name__ == "__main__":
    main(sys.argv[1:])
