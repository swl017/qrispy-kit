#!/usr/bin/env python3
"""PreToolUse(Bash) guard for destructive git and unapproved commits (RAL ticket 084, S1; widened after review rev1 B-2).

Decisions, printed as one JSON object on stdout:
  deny  - git checkout / restore / reset / clean / stash, `git switch -f|--force|--discard-changes` and
          `git checkout-index -f`, when its best-effort parser can see them. This is NOT a proof of coverage: the forms that are tested are the D series
          of test_guard_git.py and the DENY list of evidence/hook_probes/probes.py in RAL ticket 084, and a variant of the same
          category in another spelling may pass. The categories that are tested:
            plain calls, chains (; && || |), subshells and groups, quoting/escaping/absolute path, env assignments,
            git global options (-C, -c, --git-dir ...), tmux send-keys payloads;
            wrappers: sudo doas env command nohup time exec nice ionice timeout xargs builtin stdbuf chrt taskset
              setsid flock parallel watch, including options that take a value, also bundled (`sudo -iu USER`);
            shells: bash sh zsh dash ksh with -c in any flag bundle (`-lc`, `-ec`, `-c --`, `-o pipefail -c`),
              `eval`, a herestring (`bash <<< '...'`), a heredoc fed to a shell, and a pipe from echo or printf
              (`echo '...' | bash`); `su -c` and `script -c`; `find -exec/-execdir/-ok/-okdir`;
            command substitution `$(...)`, backticks and `<(...)`, also inside double quotes; backslash-newline continuations;
            git aliases (`-c alias.x=...`, `!` shell aliases, aliases in the repository's or user's git config), names case-insensitive.
  ask   - git commit / git push, except commit on a wt/* branch inside a linked git worktree (RAL ticket 084 Q-14),
          which is allowed; a wt/* branch in an ordinary clone is still asked.
  (no decision) - a plain `git commit` when the user's own chat message, within the last 30 minutes, contains a line that is only
          an approval such as `1,2,3 커밋` or `commit all`, with no later message cancelling it (RAL ticket 084 Q-42). The hook
          reads the session transcript given as `transcript_path`; only entries marked as the human's own count, never tool results,
          assistant text, summaries or messages from other sessions. The normal permission flow then applies, which the
          repository's `.claude/settings.json` allows for `git add` and `git commit`. `--amend`, `-a`/`--all` and `git push`
          are still asked, and so is everything when the transcript is missing or unreadable.
  none  - everything else (normal permission flow applies).

NOT covered (the written rules still apply; this list is examples, not a complete list, and nothing is safe just because it is not named):
  commands built through variables or `eval "$VAR"`; a shell fed by any pipe producer other than echo/printf
  (cat, curl, ...), `bash < file`, `source`/`.`, and script files; git run from an interpreter (python, perl, awk,
  node, make, ...); `env -S`; remote or container execution (ssh, docker, kubectl); an alias defined and used in the
  same command line; `git read-tree --reset -u` and other rarely used forms that overwrite the working tree;
  `git merge` / `git rebase` into main, which the repository rules reserve for the user but the hook does not ask about.

Every deny / ask / allow is appended to ~/.claude/hooks/guard.log (the M1 detection path, RAL ticket 084 Q-5).
The permission rules in settings.json block the plain forms too; this hook catches the hidden ones.
"""
import json
import os
import re
import shlex
import calendar
import subprocess
import sys
import time

BANNED = {"checkout", "restore", "reset", "clean", "stash"}
ASKED = {"commit", "push"}
WRAPPERS = {"sudo", "doas", "env", "command", "nohup", "time", "exec", "nice", "ionice", "timeout", "xargs", "builtin",
            "stdbuf", "chrt", "taskset", "setsid", "flock", "parallel", "watch"}
# wrapper options that take a separate value argument (`sudo -u USER git ...` must not stop at USER)
WRAPPER_OPTS_WITH_VALUE = {
    "sudo": {"-u", "-g", "-C", "-h", "-p", "-r", "-t", "-U", "-D", "-R", "-T", "--user", "--group", "--chdir", "--host", "--prompt", "--role", "--type"},
    "timeout": {"-s", "-k", "--signal", "--kill-after"},
    "xargs": {"-I", "-n", "-L", "-P", "-s", "-d", "-E", "-a", "--max-args", "--max-procs", "--max-lines", "--max-chars", "--delimiter", "--arg-file", "--eof"},
    "env": {"-u", "-C", "-S", "--unset", "--chdir", "--split-string"},
    "nice": {"-n", "--adjustment"},
    "time": {"-f", "-o", "--format", "--output"},
    "exec": {"-a"},
    "doas": {"-u", "-C"},
    "parallel": {"-j", "-n", "-N", "-S", "-a", "--jobs", "--max-args", "--sshlogin", "--arg-file"},
    "watch": {"-n", "--interval"},
    "stdbuf": {"-i", "-o", "-e", "--input", "--output", "--error"},
    "ionice": {"-c", "-n", "-p", "-P", "-u", "--class", "--classdata", "--pid", "--pgid", "--uid"},
    "taskset": {"-c", "-p", "--cpu-list", "--pid"},
    "flock": {"-w", "-E", "--timeout", "--conflict-exit-code"},
}
NO_NUMERIC_SKIP = {"taskset", "flock"}  # their first positional is a mask / lock file, even if it is a number
WRAPPER_POSITIONALS = {"flock": 1, "taskset": 1}  # lock file / CPU mask comes before the command (taskset: not with -c)
FIND_EXEC = {"-exec", "-execdir", "-ok", "-okdir"}
def is_force_discard(sub, a):
    """git parse-options accepts bundled short options and unambiguous long-option prefixes."""
    if sub not in ("switch", "checkout-index"):
        return False
    if a == "--force" or (not a.startswith("--") and re.match(r"^-[A-Za-z]*f", a)):
        return True
    return sub == "switch" and len(a) >= 5 and a.startswith("--di") and "--discard-changes".startswith(a)


# real git subcommands: git ignores an alias with these names, so no alias lookup is needed
KNOWN_SUBS = {"add", "am", "apply", "archive", "bisect", "blame", "branch", "bundle", "cat-file", "cherry-pick", "clone", "commit",
              "config", "describe", "diff", "difftool", "fetch", "format-patch", "gc", "grep", "hash-object", "help", "init",
              "log", "ls-files", "ls-remote", "ls-tree", "merge", "merge-base", "mv", "name-rev", "notes", "pull", "push",
              "range-diff", "rebase", "reflog", "remote", "rev-list", "rev-parse", "revert", "rm", "shortlog", "show",
              "show-ref", "sparse-checkout", "status", "submodule", "switch", "symbolic-ref", "tag", "update-index",
              "version", "whatchanged", "worktree"} | {"checkout", "restore", "reset", "clean", "stash", "checkout-index"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "!"}
SEPARATORS = {";", "&&", "||", "|", "&", "\n", "(", ")", "{", "}", "|&"}
# git global options that take a separate value argument
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--super-prefix", "--config-env"}
# regex fallback for text we cannot tokenize, and for payloads (tmux send-keys) that are not argv
BANNED_RE = re.compile(r"\bgit\b(?:\s+(?:-C\s+\S+|-c\s+\S+|--[\w-]+(?:=\S+)?|-P))*\s+(checkout|restore|reset|clean|stash)\b")
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
LOG = os.path.expanduser("~/.claude/hooks/guard.log")


SHELL_HEREDOC_RE = re.compile(r"(?:^|[\s;&|(])((?:\S*/)?(?:ba|z|da|k)?sh)((?:\s+[-+]\S+)*)\s*<<-?\s*['\"]?[A-Za-z_]")


def strip_heredocs(cmd):
    """Drop heredoc bodies: they are data written to files, not commands.
    Returns (text without bodies, bodies that are fed to a shell and therefore ARE commands)."""
    lines = cmd.split("\n")
    out, shell_bodies, i = [], [], 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        tags = [m.group(2) for m in HEREDOC_RE.finditer(line)]
        m = SHELL_HEREDOC_RE.search(line)
        feeds_shell = bool(m) and not re.search(r"-[A-Za-z]*c", m.group(2) or "")
        i += 1
        for tag in tags:
            body = []
            while i < len(lines) and lines[i].strip() != tag:
                body.append(lines[i])
                i += 1
            i += 1  # skip the terminator line
            if feeds_shell:
                shell_bodies.append("\n".join(body))
    return "\n".join(out), shell_bodies


def normalize(text):
    """What bash does before it splits words: drop backslash-newline pairs and read $'...' as '...' (outside single quotes)."""
    out, i, n, sq, dq = [], 0, len(text), False, False
    while i < n:
        c = text[i]
        if sq:
            if c == "'":
                sq = False
            out.append(c)
            i += 1
        elif c == "\\" and i + 1 < n and text[i + 1] == "\n":
            i += 2
        elif c == "\\" and i + 1 < n:
            out.append(text[i:i + 2])
            i += 2
        elif c == "$" and not dq and text.startswith("$'", i):
            sq = True
            out.append("'")
            i += 2
        elif c == "'" and not dq:
            sq = True
            out.append(c)
            i += 1
        elif c == '"':
            dq = not dq
            out.append(c)
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def substitutions(text):
    """Contents of $(...), `...`, <(...) and >(...) that bash would run, wherever they sit outside single quotes
    (including inside double quotes, which shlex hides inside one word)."""
    out, i, n, sq = [], 0, len(text), False
    while i < n:
        c = text[i]
        if sq:
            sq = c != "'"
            i += 1
        elif c == "'":
            sq = True
            i += 1
        elif c == "\\":
            i += 2
        elif (text.startswith("$(", i) and not text.startswith("$((", i)) or text[i:i + 2] in ("<(", ">("):
            j, depth, q = i + 2, 1, ""
            while j < n and depth:
                d = text[j]
                if q:
                    q = "" if d == q else q
                elif d in "'\"":
                    q = d
                elif d == "\\":
                    j += 1
                elif d == "(":
                    depth += 1
                elif d == ")":
                    depth -= 1
                j += 1
            out.append(text[i + 2:j - 1] if depth == 0 else text[i + 2:])
            i = j
        elif c == "`":
            j = i + 1
            while j < n and text[j] != "`":
                j += 2 if text[j] == "\\" else 1
            out.append(text[i + 1:j])
            i = j + 1
        else:
            i += 1
    return out


def tokenize(cmd):
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|()`\n")
    lex.whitespace = " \t\r"  # newlines are separators, not whitespace
    lex.whitespace_split = True
    lex.commenters = ""  # shlex comments swallow the newline and merge two commands
    toks = []
    for t in lex:
        toks.append(t)
    return toks


def segments(tokens):
    """Yield (segment, separator that precedes it); the separator tells a pipe from a plain sequence."""
    seg, sep = [], ""
    for t in tokens:
        if t in SEPARATORS or set(t) <= set(";&|()`\n"):
            if seg:
                yield seg, sep
            seg, sep = [], t
        else:
            seg.append(t)
    if seg:
        yield seg, sep


def strip_prefix(argv):
    """Skip env assignments and wrapper commands (sudo -iu USER, env -u X, timeout -s KILL 5, xargs -I {}, flock LOCK, ...)."""
    i = 0
    while i < len(argv):
        a = argv[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", a) or a in KEYWORDS:
            i += 1
        elif os.path.basename(a) in WRAPPERS:
            base = os.path.basename(a)
            valued = WRAPPER_OPTS_WITH_VALUE.get(base, set())
            valued_letters = {o[1] for o in valued if len(o) == 2}
            seen_c = False
            i += 1
            while i < len(argv):
                t = argv[i]
                if t == "--":
                    i += 1
                    break
                if t in valued:
                    seen_c = seen_c or t in ("-c", "--cpu-list")
                    i += 2
                elif re.fullmatch(r"-[A-Za-z]{2,}", t) and t[-1] in valued_letters:  # bundled: `sudo -iu USER`, `sudo -Eu USER`
                    i += 2
                elif t.startswith("-") or (base not in NO_NUMERIC_SKIP and re.match(r"^\d+(\.\d+)?[smhd]?$", t)):
                    i += 1
                else:
                    break
            i += 0 if (base == "taskset" and seen_c) else WRAPPER_POSITIONALS.get(base, 0)
        else:
            break
    return argv[i:]


def shell_command_string(argv):
    """For a shell argv return (command string of -c, reads_stdin). `bash -lc CMD`, `sh -xc CMD`, `bash -c -- CMD` all give CMD."""
    i, c_seen, s_seen = 1, False, False
    while i < len(argv):
        t = argv[i]
        if t == "--":
            i += 1
            break
        if t.startswith("--"):
            i += 2 if t in ("--rcfile", "--init-file") else 1
        elif len(t) > 1 and t[0] in "-+":
            c_seen = c_seen or (t[0] == "-" and "c" in t[1:])
            s_seen = s_seen or (t[0] == "-" and "s" in t[1:])
            i += 2 if t[-1] in "oO" else 1
        else:
            break
    if c_seen:
        return (argv[i] if i < len(argv) else None), False
    if s_seen or i >= len(argv):
        return None, True  # reads commands from standard input
    return None, False  # runs a script file: not visible to this hook


def valued_command_string(argv):
    """`su -c CMD USER`, `script -qc CMD FILE`: the option whose value is a command line."""
    for k, t in enumerate(argv[1:], 1):
        if t == "--command" and k + 1 < len(argv):
            return argv[k + 1]
        if t.startswith("--command="):
            return t.split("=", 1)[1]
        if re.fullmatch(r"-[A-Za-z]*c", t) and k + 1 < len(argv):
            return argv[k + 1]
    return None


def git_subcommand(argv):
    """Return (subcommand, -C dir or None, {alias: value} from `-c alias.x=...`, args after the subcommand)."""
    if not argv or os.path.basename(argv[0]) != "git":
        return None, None, {}, []
    i, cdir, aliases = 1, None, {}
    while i < len(argv):
        a = argv[i]
        if a in GIT_OPTS_WITH_VALUE:
            val = argv[i + 1] if i + 1 < len(argv) else ""
            if a == "-C" and val:
                cdir = val if cdir is None else os.path.join(cdir, val)
            elif a == "-c":
                m = re.match(r"^alias\.([^=]+)=(.*)$", val, re.S | re.I)
                if m:
                    aliases[m.group(1).lower()] = m.group(2)
            i += 2
        elif a.startswith("-"):
            i += 1
        else:
            return a, cdir, aliases, argv[i + 1:]
    return None, cdir, aliases, []


_CONFIG_ALIASES = {}


def config_aliases(repo):
    """Aliases from the repository's and the user's git config (looked up only for names that are not real subcommands)."""
    if repo not in _CONFIG_ALIASES:
        found = {}
        try:
            out = subprocess.run(["git", "-C", repo, "config", "--get-regexp", r"^alias\."], capture_output=True, text=True, timeout=3)
            for line in out.stdout.splitlines():
                key, _, val = line.partition(" ")
                found[key[len("alias."):]] = val
        except Exception:
            pass
        _CONFIG_ALIASES[repo] = found
    return _CONFIG_ALIASES[repo]


def resolve_alias(sub, rest, aliases, repo, depth=0):
    """Follow git aliases. Returns (subcommand, args, shell_body): shell_body is set for `!` aliases and must be analysed as a command."""
    while depth < 4 and sub not in KNOWN_SUBS:
        val = aliases.get(sub.lower())
        if val is None:
            val = config_aliases(repo).get(sub.lower())
        if val is None:
            break
        if val.startswith("!"):
            return None, rest, val[1:]
        try:
            parts = shlex.split(val)
        except ValueError:
            break
        if not parts:
            break
        sub, rest, depth = parts[0], parts[1:] + rest, depth + 1
    return sub, rest, None


def branch_of(path):
    try:
        out = subprocess.run(["git", "-C", path, "symbolic-ref", "--short", "-q", "HEAD"],
                             capture_output=True, text=True, timeout=3)
        return out.stdout.strip() if out.returncode == 0 else None
    except Exception:
        return None


def is_linked_worktree(path):
    """True only for a linked worktree (`git worktree add`), whose git-dir differs from the common dir."""
    try:
        out = subprocess.run(["git", "-C", path, "rev-parse", "--absolute-git-dir", "--git-common-dir"],
                             capture_output=True, text=True, timeout=3)
        if out.returncode != 0:
            return False
        gd, common = out.stdout.split("\n")[:2]
        common = os.path.normpath(os.path.join(path, common)) if not os.path.isabs(common) else common
        return os.path.realpath(gd) != os.path.realpath(common)
    except Exception:
        return False


def unescape(text):
    """printf / echo -e escapes that matter for splitting a command line."""
    return text.replace("\\n", "\n").replace("\\t", " ").replace("\\\\", "\\")


# A plain commit is allowed when the user said so in chat (RAL ticket 084 Q-42). The hook cannot see the chat, but PreToolUse
# input carries the session transcript path; user messages are the entries marked origin.kind == "human".
TRANSCRIPT = None
APPROVAL_WINDOW_S = 30 * 60
TAIL_BYTES = 8 * 1024 * 1024
# A leading list number ("1. ", "2) ") is allowed: users answer a numbered question list item by item ("1. 1 커밋"),
# PAPER1 ticket 002, 2026-10-18 (lesson L-023). One or two digits only, so "2024. 커밋" is not an approval.
# Earlier clauses of the same line, ended by "," ";" or "/" and a space, may carry other decisions: users answer a mixed
# list on one line ("1 종결, 1,2 커밋"), PAPER1 ticket 004, 2026-10-19. The approval must still be the last clause, and
# CANCEL_LINE still vetoes the whole message.
# An earlier clause may also end in a Korean connective ending (-고, -니, -서) and a space, with no punctuation: "006 닫고
# 1,2 커밋", PAPER1 ticket 006, 2026-10-31 (lesson L-023). A conditional ending (-면) is not accepted, and a deferral word
# before the approval on the same line ("나중에", "끝나고", "후에" …) vetoes the message through CANCEL_LINE.
_PRIOR = r"(?:.*?(?:[,;/]\s+|(?<=[고니서])\s+))?"
APPROVE_LINE = re.compile(
    r"^[\s>*\-]*(?:\d{1,2}[.)]\s+)?" + _PRIOR + r"(?:(?:[\d\s,·/와과및]+만?|모두|전부|전체|all)\s*)?(?:묶음\s*)?커밋"
    r"(?:\s*(?:해줘|해 줘|해주세요|해|하자|하세요|진행해|진행|해도\s*돼|ㄱㄱ))?[\s.!~]*$"
    r"|^[\s>*\-]*(?:\d{1,2}[.)]\s+)?" + _PRIOR + r"commit(?:\s+(?:all|them|it|groups?\s*[\d,\s]+))?[\s.!]*$", re.I)
CANCEL_LINE = re.compile(r"커밋\s*(?:하지\s*마|하지마|말아|말고|취소|보류|아직|나중|금지)|(?:don'?t|do not|not yet|cancel|hold off)\s+commit"
                         r"|(?:나중|이따|다음에|내일|아직|보류|대기|기다리|끝나고|끝나면|되면|하면|전에|후에|뒤에)[^\n]*?커밋", re.I)
# Text the human did not type: the harness wraps pasted content and IDE notices in tags. The pasted block carries a random id
# on both tags, so a fake closing tag inside a paste does not end it early. Whatever is left is what the user wrote.
PASTED_BLOCK = re.compile(r'<pasted_content id="([^"]*)">.*?</pasted_content id="\1">', re.S)
TAG_BLOCK = re.compile(r"<([A-Za-z_][\w-]*)\b[^>]*>.*?</\1\b[^>]*>", re.S)
COMMIT_VALUE_OPTS = {"--message", "--file", "--reuse-message", "--reedit-message", "--template", "--author", "--date",
                     "--cleanup", "--fixup", "--squash", "--trailer"}


def human_text(e):
    """The user's own text in a transcript entry, or None when the entry is not a human message."""
    if e.get("type") == "user":
        if (e.get("origin") or {}).get("kind") != "human":
            return None
        c = (e.get("message") or {}).get("content")
    elif e.get("type") == "attachment":  # a message typed while the agent was working
        a = e.get("attachment") or {}
        if a.get("type") != "queued_command" or (a.get("origin") or {}).get("kind") != "human":
            return None
        c = a.get("prompt")
    else:
        return None
    if isinstance(c, list):
        c = "\n".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    if not isinstance(c, str):
        return None
    return TAG_BLOCK.sub("", PASTED_BLOCK.sub("", c))


def commit_approval(path, now=None):
    """The approving line of the newest human message that mentions committing, or None (fail safe: None)."""
    if not path:
        return None
    now = time.time() if now is None else now
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - TAIL_BYTES))
            raw = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    for line in reversed(raw.splitlines()):
        if '"human"' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        text = human_text(e)
        if text is None:
            continue
        stamp = e.get("timestamp") or (e.get("attachment") or {}).get("timestamp") or ""
        try:
            when = calendar.timegm(time.strptime(stamp[:19], "%Y-%m-%dT%H:%M:%S"))
        except ValueError:
            return None
        if now - when > APPROVAL_WINDOW_S:
            return None  # newest first: everything further back is older still
        lines = [x.strip() for x in text.splitlines()]
        if any(CANCEL_LINE.search(x) for x in lines):
            return None
        for x in lines:
            if APPROVE_LINE.match(x):
                return x
    return None


def commit_is_plain(rest):
    """False for `git commit --amend` and `-a`/`--all` (rewrites a commit, or stages other sessions' files)."""
    skip = False
    for t in rest:
        if skip:
            skip = False
            continue
        if t == "--":
            break
        if t in ("--amend", "--all") or t.startswith("--amend="):
            return False
        if t.startswith("--"):
            skip = t in COMMIT_VALUE_OPTS
            continue
        if t.startswith("-") and len(t) > 1:
            for k, ch in enumerate(t[1:]):
                if ch == "a":
                    return False
                if ch in "mFCct":  # takes a value: the rest of this token, or the next token
                    skip = (k == len(t) - 2)
                    break
    return True


_approval_cache = []


def approval_line():
    if not _approval_cache:
        _approval_cache.append(commit_approval(TRANSCRIPT))
    return _approval_cache[0]


def scan_argv(argv, here, depth, piped_from=None):
    """Decisions for one command (argv already stripped of env assignments and wrappers).
    piped_from: argv of the command on the left of a `|`, if any (for `echo 'git ...' | bash`)."""
    found = []
    prog = os.path.basename(argv[0])
    if prog in SHELLS and depth < 3:
        head = argv
        for k, a in enumerate(argv):  # herestring: the string after <<< is what the shell runs (glued or separate)
            if a.startswith("<<<"):
                head = argv[:k]
                word = a[3:] or (argv[k + 1] if k + 1 < len(argv) else "")
                if word:
                    found += analyse(word, here, depth + 1)
                break
        cmd, reads_stdin = shell_command_string(head)
        if cmd is not None:
            found += analyse(cmd, here, depth + 1)
        elif reads_stdin and piped_from:
            src = strip_prefix(piped_from)
            if src and os.path.basename(src[0]) == "echo":
                found += analyse(unescape(" ".join(a for a in src[1:] if not a.startswith("-"))), here, depth + 1)
            elif src and os.path.basename(src[0]) == "printf":  # printf FORMAT ARG...: each argument may be a command line
                for a in src[1:]:
                    if not a.startswith("-"):
                        found += analyse(unescape(a), here, depth + 1)
        return found
    if prog in ("su", "script") and depth < 3:
        cmd = valued_command_string(argv)
        return analyse(cmd, here, depth + 1) if cmd else found
    if prog == "eval" and depth < 3:
        return analyse(" ".join(argv[1:]), here, depth + 1)
    if prog == "tmux" and ("send-keys" in argv or "send" in argv):
        k = argv.index("send-keys") if "send-keys" in argv else argv.index("send")
        i = k + 1
        while i < len(argv) and argv[i].startswith("-"):  # tmux options: -t TARGET, -N COUNT, -c CLIENT take a value
            i += 2 if argv[i] in ("-t", "-N", "-c") else 1
        payload = " ".join(argv[i:])
        if BANNED_RE.search(payload):
            found.append(("deny", "tmux send-keys payload contains a banned git subcommand"))
        elif depth < 3:  # what is typed into the other window is a command line too
            found += analyse(payload, here, depth + 1)
        return found
    if prog == "find" and depth < 3:  # `find ... -exec CMD ARGS {} ;|+` runs CMD
        for k, a in enumerate(argv):
            if a in FIND_EXEC:
                sub = []
                for t in argv[k + 1:]:
                    if t in (";", "+"):
                        break
                    sub.append(t)
                sub = strip_prefix(sub)
                if sub:
                    found += scan_argv(sub, here, depth + 1)
        return found
    sub, cdir, aliases, rest = git_subcommand(argv)
    if sub is None:
        return found
    repo = os.path.normpath(os.path.join(here, os.path.expanduser(cdir))) if cdir else here
    sub, rest, shell_body = resolve_alias(sub, rest, aliases, repo)
    if shell_body is not None:
        return found + analyse(shell_body, repo, depth + 1) if depth < 3 else found
    if sub in BANNED:
        found.append(("deny", f"git {sub} is banned (destroys uncommitted work with no recovery); use git switch to change branches"))
    elif any(is_force_discard(sub, a) for a in rest):
        found.append(("deny", f"git {sub} with a force/discard option overwrites uncommitted work with no recovery"))
    elif sub in ASKED:
        br = branch_of(repo)
        if sub == "commit" and br and br.startswith("wt/") and is_linked_worktree(repo):
            found.append(("allow", f"commit on wt/* branch {br} inside a linked git worktree"))
        elif sub == "commit" and commit_is_plain(rest) and approval_line():
            found.append(("approved", f"commit approved in chat: {approval_line()!r}"))
        else:
            found.append(("ask", f"git {sub} on branch {br or 'unknown'} needs explicit user permission"))
    return found


def analyse(cmd, cwd, depth=0):
    """Return list of (decision, reason) found in cmd."""
    found = []
    try:
        text, shell_bodies = strip_heredocs(cmd)
        text = normalize(text)
        toks = tokenize(text)
        if depth < 3:
            for body in shell_bodies:  # `bash <<EOF ... EOF`: the body is a command, not data
                found += analyse(body, cwd, depth + 1)
            for inner in substitutions(text):  # $(...) and backticks, also inside double quotes
                found += analyse(inner, cwd, depth + 1)
    except ValueError:
        if BANNED_RE.search(cmd):
            found.append(("deny", "unparseable command containing a banned git subcommand"))
        elif re.search(r"\bgit\b[^\n;&|]*\b(commit|push)\b", cmd):
            found.append(("ask", "unparseable command containing git commit/push"))
        return found
    here = cwd
    prev = None
    for seg, sep in segments(toks):
        argv = strip_prefix(seg)
        piped = prev if sep in ("|", "|&") else None
        prev = seg
        if not argv:
            continue
        if os.path.basename(argv[0]) == "cd" and len(argv) > 1:
            here = os.path.normpath(os.path.join(here, os.path.expanduser(argv[1])))
            continue
        found += scan_argv(argv, here, depth, piped)
    return found


def decide(found):
    for d in ("deny", "ask", "allow", "approved"):
        hits = [r for (x, r) in found if x == d]
        if hits:
            return d, "; ".join(dict.fromkeys(hits))
    return None, None


def log(decision, reason, cwd, cmd):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "decision": decision,
                                "reason": reason, "cwd": cwd, "cmd": cmd[:500]}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    cwd = data.get("cwd") or os.getcwd()
    global TRANSCRIPT
    TRANSCRIPT = data.get("transcript_path")
    try:
        decision, reason = decide(analyse(cmd, cwd))
    except Exception as exc:  # never fail open on a banned command because the parser broke
        if BANNED_RE.search(cmd):
            decision, reason = "deny", f"parser error ({type(exc).__name__}); regex fallback found a banned git subcommand"
        elif re.search(r"\bgit\b[^\n;&|]*\b(commit|push)\b", cmd):  # the repository allows git commit, so this hook is the gate
            decision, reason = "ask", f"parser error ({type(exc).__name__}); command contains git commit/push"
        else:
            decision, reason = None, None
    if decision is None:
        return 0
    if decision == "approved":  # print nothing: the permission flow decides, and the repository allows git commit
        log("approved", reason, cwd, cmd)
        return 0
    log(decision, reason, cwd, cmd)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": decision,
                                             "permissionDecisionReason": f"[qrispy guard] {reason}"}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
