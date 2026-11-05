#!/usr/bin/env python3
"""qrispy_config — the repository's ticket systems, read from `qrispy.json` at the repository root (RAL ticket 089).

Every workflow tool of the kit (lib/qrispy.py, lib/launch.py, lib/gpu_lock.py, lib/jobs/review_headless.sh)
takes system names and ticket folders from here, so a repository needs only its own qrispy.json. The repository
is the nearest folder at or above the working folder that holds a qrispy.json, or $QRISPY_REPO when set
(RAL ticket 090): the tools live in the kit, not in the repository they work on. The first system is the primary one: its tickets are named by slug in a review
round, and the *.md files directly in its folder are the shared method documents. A missing or malformed file
stops the tool with the reason; there is no silent default (a repository that forgot the file must not run as RAL).

CLI for shell scripts:
    qrispy_config.py ticket-dir <NNN-slug | <root>/NNN-slug>   the ticket folder relative to the repository
    qrispy_config.py primary-root | review-scratch | external-roots | repo
Library: find_repo() -> path; load(repo) -> Config; claude_project_dir(repo).
"""
import json
import os
import re
import sys

NAME_RE = re.compile(r"^[A-Z][A-Z0-9]*$")
SLUG_RE = re.compile(r"^\d{3}-[A-Za-z0-9._-]+$")
LIB = os.path.dirname(os.path.abspath(__file__))  # the kit's tools
PLUGIN = os.path.dirname(LIB)                      # the plugin folder (skills/, agents/, hooks/, bin/)


class ConfigError(Exception):
    pass


def find_repo(start=None):
    """$QRISPY_REPO, else the nearest folder at or above `start` (default: the working folder) with a qrispy.json."""
    env = os.environ.get("QRISPY_REPO")
    if env:
        return os.path.abspath(env)
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(d, "qrispy.json")):
            return d
        up = os.path.dirname(d)
        if up == d:
            raise ConfigError(f"no qrispy.json in {os.path.abspath(start or os.getcwd())} or any parent folder; "
                              "run `qrispy init` there, or set QRISPY_REPO")
        d = up


class Config:
    def __init__(self, repo, data):
        self.repo = repo
        self.systems = [(s["name"], s["root"]) for s in data["systems"]]  # ordered; the first is the primary
        self.external = [(s["name"], os.path.expanduser(s["root"])) for s in data.get("external_systems") or []]
        self.known_dups = {k: set(v) for k, v in (data.get("known_duplicate_numbers") or {}).items()}
        self.review_scratch = data["review_scratch"]  # required: no silent default (RAL ticket 089 rev1 A1-3)
        self.names = [n for n, _ in self.systems]
        self.root_of = dict(self.systems)
        self.system_of_root = {r: n for n, r in self.systems}
        self.primary, self.primary_root = self.systems[0]

    def abs_roots(self):
        return [(n, os.path.join(self.repo, r)) for n, r in self.systems]

    def names_alt(self, external=False):
        """Regex alternation of the system names, e.g. 'DEMO|SIDE|OTHER'."""
        return "|".join(re.escape(n) for n in self.names + ([n for n, _ in self.external] if external else []))

    def roots_alt(self):
        """Regex alternation of the ticket folders, longest first."""
        return "|".join(re.escape(r) for r in sorted(self.system_of_root, key=len, reverse=True))

    def names_text(self):
        """'DEMO, SIDE or OTHER'."""
        return self.names[0] if len(self.names) == 1 else ", ".join(self.names[:-1]) + " or " + self.names[-1]

    def system_of_dir(self, path):
        """The system whose ticket folder `path` (absolute, or ending in the folder) is; longest folder first,
        since 'tickets' is also the end of 'side/tickets'. None when no folder matches."""
        p = os.path.normpath(path).replace(os.sep, "/")
        for r in sorted(self.system_of_root, key=len, reverse=True):
            if p == r or p.endswith("/" + r):
                return self.system_of_root[r]
        return None

    def ticket_dir(self, ref):
        """A primary-system slug or '<root>/<NNN-slug>' -> the ticket folder relative to the repository."""
        if SLUG_RE.match(ref):
            return f"{self.primary_root}/{ref}"
        root, _, slug = ref.rstrip("/").rpartition("/")
        if root in self.system_of_root and root != self.primary_root and SLUG_RE.match(slug):  # a primary ticket goes by its slug only
            return f"{root}/{slug}"
        raise ConfigError(f"not a ticket slug of {self.primary} or a path <root>/NNN-slug with a root in qrispy.json: {ref}")


def load(repo=None):
    repo = repo or find_repo()
    path = os.path.join(repo, "qrispy.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"no qrispy.json at {repo} (the repository's ticket systems; see the kit README)")
    except ValueError as e:
        raise ConfigError(f"{path} is not valid JSON: {e}")
    systems = data.get("systems") if isinstance(data, dict) else None
    if not systems or not isinstance(systems, list):
        raise ConfigError(f"{path}: 'systems' must be a non-empty list")
    if not isinstance(data.get("review_scratch"), str) or not data["review_scratch"]:
        raise ConfigError(f"{path}: 'review_scratch' (the parent folder of review-round scratch folders) is required")
    names, roots = set(), set()
    for s in systems + list(data.get("external_systems") or []):
        n, r = (s.get("name"), s.get("root")) if isinstance(s, dict) else (None, None)
        if not isinstance(n, str) or not NAME_RE.match(n):
            raise ConfigError(f"{path}: system name {n!r} must match {NAME_RE.pattern}")
        if not isinstance(r, str) or not r:
            raise ConfigError(f"{path}: system {n} has no root")
        if n in names:
            raise ConfigError(f"{path}: system name {n} appears twice")
        names.add(n)
    for s in systems:
        r = s["root"]
        if os.path.isabs(r) or r.startswith("~") or ".." in r.split("/") or r != r.strip("/"):
            raise ConfigError(f"{path}: root {r!r} of {s['name']} must be a relative path inside the repository")
        if r in roots:
            raise ConfigError(f"{path}: root {r} appears twice")
        roots.add(r)
    return Config(repo, data)


def load_or_exit(repo=None, prog="qrispy"):
    try:
        return load(repo)
    except ConfigError as e:
        sys.exit(f"{prog}: {e}")


def claude_project_dir(repo):
    """~/.claude/projects/<name>: Claude Code names a project's folder after its absolute path with every
    character that is not a letter or a digit replaced by '-'."""
    return os.path.join(os.path.expanduser("~/.claude/projects"), re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(repo)))


def pid_alive(pid):
    """Whether process `pid` exists, without /proc (macOS has none, RAL ticket 089). A process of another user counts as alive."""
    try:
        pid = int(pid)
        if pid <= 0:  # os.kill(0, 0) would signal our own process group
            return False
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (OSError, ValueError, OverflowError):
        return False


def parent_pid(pid):
    """The parent of `pid` from /proc, else from `ps` (macOS); None when unknown."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            return int(f.read().rsplit(")", 1)[1].split()[1])  # field 4: parent pid
    except (OSError, ValueError, IndexError):
        pass
    try:
        import subprocess
        out = subprocess.run(["ps", "-o", "ppid=", "-p", str(pid)], capture_output=True, text=True, timeout=5).stdout.strip()
        return int(out) if out else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def main(argv):
    cfg = load_or_exit(None, "qrispy_config")
    cmd, rest = (argv[0], argv[1:]) if argv else ("", [])
    if cmd == "repo" and not rest:
        print(cfg.repo)
    elif cmd == "ticket-dir" and len(rest) == 1:
        try:
            print(cfg.ticket_dir(rest[0]))
        except ConfigError as e:
            sys.exit(f"qrispy_config: {e}")
    elif cmd == "primary-root" and not rest:
        print(cfg.primary_root)
    elif cmd == "review-scratch" and not rest:
        print(cfg.review_scratch)
    elif cmd == "external-roots" and not rest:
        print("\n".join(r for _, r in cfg.external))
    else:
        sys.exit(__doc__.split("Library:")[0].split("CLI for shell scripts:")[1].rstrip())


if __name__ == "__main__":
    main(sys.argv[1:])
