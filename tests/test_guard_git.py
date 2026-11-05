#!/usr/bin/env python3
"""Unit tests for guard_git.py (RAL ticket 084, S1). Run: python3 -I test_guard_git.py <scratch_dir>"""
import json
import os
import subprocess
import sys

sys.dont_write_bytecode = True  # importing guard_git must not leave __pycache__ in the repository (RAL 084 rev1 A-10)

HERE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugin", "hooks")  # the guard lives in the kit's plugin (RAL ticket 090)
sys.path.insert(0, HERE)
import guard_git  # noqa: E402

import tempfile  # noqa: E402

scratch = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="guard_git_test_")  # fresh each run: git worktree add fails on a reused scratch dir
main_repo = os.path.join(scratch, "repo_main")
wt_repo = os.path.join(scratch, "repo_wt")
for path, branch in ((main_repo, "main"), (wt_repo, "wt/084-demo")):
    os.makedirs(path, exist_ok=True)
    subprocess.run(["git", "init", "-q", path], check=True)  # git 2.25 has no `init -b`
    subprocess.run(["git", "-C", path, "symbolic-ref", "HEAD", "refs/heads/" + branch], check=True)
# a real linked worktree (the only place where wt/* commits are free), made from main_repo
subprocess.run(["git", "-C", main_repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "--allow-empty", "-m", "init"], check=True)
linked = os.path.join(scratch, "repo_linked")
subprocess.run(["git", "-C", main_repo, "worktree", "add", "-q", "-b", "wt/084-linked", linked], check=True)

CASES = [
    # (id, command, cwd, expected decision)
    ("D01", "git checkout -- .", main_repo, "deny"),
    ("D02", "git -C /some/repo checkout -- . 2>/dev/null", main_repo, "deny"),
    ("D03", "cd /tmp/mirror && git restore file.py", main_repo, "deny"),
    ("D04", "ls; git reset --hard HEAD", main_repo, "deny"),
    ("D05", "git clean -fdx", main_repo, "deny"),
    ("D06", "git stash list", main_repo, "deny"),
    ("D07", "bash -c 'git checkout main'", main_repo, "deny"),
    ("D08", "sudo git reset HEAD~1", main_repo, "deny"),
    ("D09", "GIT_DIR=x git stash", main_repo, "deny"),
    ("D10", "echo hi | (cd x && git checkout -b foo)", main_repo, "deny"),
    ("D11", "tmux send-keys -t sim:0 'git checkout -- .' Enter", main_repo, "deny"),
    ("D12", "git -c core.pager=cat --no-pager checkout .", main_repo, "deny"),
    ("D13", "x=$(git stash)", main_repo, "deny"),
    ("D14", "echo `git restore a`", main_repo, "deny"),
    ("D15", "sh -c \"cd /r && git clean -n\"", main_repo, "deny"),
    ("D16", "timeout 5 git reset", main_repo, "deny"),
    ("D17", "ls # list\ngit checkout x", main_repo, "deny"),
    ("D18", "for f in a b; do git restore $f; done", main_repo, "deny"),
    ("D19", "eval git stash pop", main_repo, "deny"),
    ("D21", "if true; then git checkout x; fi", main_repo, "deny"),
    ("D22", "while read f; do echo $f; done < l; ! git stash", main_repo, "deny"),
    ("D20", "echo 'unbalanced && git checkout -- .", main_repo, "deny"),
    # RAL 084 rev1 B-2 / A-1: forms that passed with no decision before the 2026-10-17 fix
    ("D23", "find . -name f -exec git checkout -- {} +", main_repo, "deny"),
    ("D24", "timeout -s KILL 5 git reset --hard", main_repo, "deny"),
    ("D25", "sudo -u usrg git reset --hard", main_repo, "deny"),
    ("D26", "xargs -I {} git checkout {}", main_repo, "deny"),
    ("D27", "git -c alias.co=checkout co -- .", main_repo, "deny"),
    ("D28", "git -c 'alias.zap=!git clean -fdx' zap", main_repo, "deny"),
    ("D29", "git switch --discard-changes main", main_repo, "deny"),
    ("D30", "git switch -f main", main_repo, "deny"),
    ("D31", "git checkout-index -f -a", main_repo, "deny"),
    ("D32", "find . -execdir git stash \\;", main_repo, "deny"),
    ("D33", "timeout --signal=KILL 5 git clean -fd", main_repo, "deny"),
    ("D34", "sudo -g wheel -u root git restore f", main_repo, "deny"),
    ("D35", "env -u FOO git checkout x", main_repo, "deny"),
    ("D36", "xargs -n 1 git restore", main_repo, "deny"),
    ("D37", "git switch --force main", main_repo, "deny"),
    ("A05", "timeout -s KILL 5 git commit -m x", main_repo, "ask"),
    # RAL 084 rev2 R2-B1: shell flags, stdin to a shell, bundled wrapper options, more wrappers
    ("D38", "bash -lc 'git checkout -- .'", main_repo, "deny"),
    ("D39", "bash -ec 'git reset --hard'", main_repo, "deny"),
    ("D40", "sh -xc 'git stash'", main_repo, "deny"),
    ("D41", "bash -c -- 'git checkout -- .'", main_repo, "deny"),
    ("D42", "echo 'git checkout -- .' | bash", main_repo, "deny"),
    ("D43", "bash <<< 'git checkout -- .'", main_repo, "deny"),
    ("D44", "bash <<'X'\ngit checkout -- .\nX", main_repo, "deny"),
    ("D45", "sudo -iu usrg git reset --hard", main_repo, "deny"),
    ("D46", "sudo -Eu usrg git reset --hard", main_repo, "deny"),
    ("D47", "stdbuf -oL git checkout -- .", main_repo, "deny"),
    ("D48", "ionice -c3 git reset --hard", main_repo, "deny"),
    ("D49", "su -c 'git reset --hard' usrg", main_repo, "deny"),
    ("D50", "script -qc 'git checkout -- .' /dev/null", main_repo, "deny"),
    ("D51", "printf '%s\\n' 'git clean -fdx' | sh", main_repo, "deny"),
    ("D52", "taskset 0x3 git checkout x", main_repo, "deny"),
    ("D53", "flock /tmp/lock git stash", main_repo, "deny"),
    ("D54", "setsid git restore f", main_repo, "deny"),
    ("D55", "bash -o pipefail -c 'git stash'", main_repo, "deny"),
    ("D56", "sudo bash -lc 'git checkout x'", main_repo, "deny"),
    ("D57", "bash --login -c 'git restore f'", main_repo, "deny"),
    ("D58", "sh -s <<< 'git stash'", main_repo, "deny"),
    ("D59", "taskset -c 0,1 git clean -fd", main_repo, "deny"),
    ("D60", "sudo -u usrg bash -c 'cd /r && git reset --hard'", main_repo, "deny"),
    ("D61", "parallel git checkout ::: a b", main_repo, "deny"),
    ("D62", "watch -n 1 git stash", main_repo, "deny"),
    # RAL 084 rev3 R3-B1: structural gaps (line continuation, quoted substitution) and category variants
    ("D63", "git \\\n  checkout -- .", main_repo, "deny"),
    ("D64", "git -C /x \\\n  reset --hard", main_repo, "deny"),
    ("D65", "git switch \\\n  -f main", main_repo, "deny"),
    ("D66", 'out="$(git stash)"', main_repo, "deny"),
    ("D67", 'echo "$(git reset --hard)"', main_repo, "deny"),
    ("D68", 'echo "`git stash`"', main_repo, "deny"),
    ("D69", "bash <<<'git checkout -- .'", main_repo, "deny"),
    ("D70", "/bin/bash <<'X'\ngit checkout -- .\nX", main_repo, "deny"),
    ("D71", "printf 'git stash\\n' | bash", main_repo, "deny"),
    ("D72", "taskset 1 git reset --hard", main_repo, "deny"),
    ("D73", "taskset 3 git checkout x", main_repo, "deny"),
    ("D74", "tmux send-keys -t s:0 'git switch -f main' Enter", main_repo, "deny"),
    ("D75", "tmux send -t s:0 'git reset --hard' Enter", main_repo, "deny"),
    ("D76", "git checkout-index -af", main_repo, "deny"),
    ("D77", "git checkout-index -fa", main_repo, "deny"),
    ("D78", "git switch --discard main", main_repo, "deny"),
    ("D79", "git -c ALIAS.co=checkout co x", main_repo, "deny"),
    ("D80", "git -c alias.CO=checkout co x", main_repo, "deny"),
    ("D81", "git $'reset' --hard", main_repo, "deny"),
    ("D82", "cat <(git stash)", main_repo, "deny"),
    ("D83", "echo \"a $(echo $(git clean -fd))\"", main_repo, "deny"),
    ("A06", "bash -lc 'git commit -m x'", main_repo, "ask"),
    ("A01", "git commit -m 'msg'", main_repo, "ask"),
    ("A02", "git push origin main", wt_repo, "ask"),
    ("A03", f"git -C {main_repo} commit -m x", wt_repo, "ask"),
    ("A04", "git add a && git commit -m x", main_repo, "ask"),
    ("W01", "git commit -m 'wip'", wt_repo, "ask"),  # wt/* branch but an ordinary clone: not the exception
    ("W02", "git commit -m 'wip'", linked, "allow"),
    ("W03", f"cd {linked} && git commit -am x", main_repo, "allow"),
    ("W04", f"git -C {linked} commit -m x", main_repo, "allow"),
    ("W05", f"git -C {linked} push origin wt/084-linked", main_repo, "ask"),
    ("N01", "git status", main_repo, None),
    ("N02", "git log --oneline -5", main_repo, None),
    ("N03", "git switch -c wt/084-x", main_repo, None),
    ("N04", "git worktree add ../wt -b wt/084-x", main_repo, None),
    ("N05", "grep -n 'git checkout' CLAUDE.md", main_repo, None),
    ("N06", "echo \"never run git reset\"", main_repo, None),
    ("N07", "cat > notes.md <<'EOF'\nDo not run git checkout -- .\ngit stash is banned\nEOF\nwc -l notes.md", main_repo, None),
    ("N08", "python3 -c \"print('git restore')\"", main_repo, None),
    ("N09", "git diff --stat", main_repo, None),
    ("N10", "ls checkout reset", main_repo, None),
    ("N11", "git show HEAD:tickets/COORDINATION.md | head", main_repo, None),
    ("N12", "rg 'git (checkout|stash)' -n .", main_repo, None),
    ("N14", "if git diff --quiet; then echo clean; fi", main_repo, None),
    ("N13", "git log --grep='checkout'", main_repo, None),
    ("N15", "find . -name '*.pyc' -exec rm {} +", main_repo, None),
    ("N16", "sudo -u usrg ls", main_repo, None),
    ("N17", "timeout -s KILL 5 git status", main_repo, None),
    ("N18", "xargs -I {} echo {}", main_repo, None),
    ("N19", "git -c core.pager=cat log -1", main_repo, None),
    ("N20", "git switch main", main_repo, None),
    ("N21", "git -c alias.st=status st", main_repo, None),
    ("N22", "find . -exec grep -l 'git checkout' {} +", main_repo, None),
    ("N23", "bash script.sh", main_repo, None),
    ("N24", "cat <<EOF > f\ngit checkout x\nEOF", main_repo, None),
    ("N25", "python3 - <<'EOF'\nimport os\nEOF", main_repo, None),
    ("N26", "bash -lc 'ls -l'", main_repo, None),
    ("N27", "sudo -iu usrg ls", main_repo, None),
    ("N28", "ionice -c3 nice ls", main_repo, None),
    ("N29", "su -c 'ls' usrg", main_repo, None),
    ("N30", "bash <<< 'echo hi'", main_repo, None),
    ("N31", "stdbuf -oL ls", main_repo, None),
    ("N32", "flock /tmp/lock ls", main_repo, None),
    ("N33", "echo 'git checkout' | cat", main_repo, None),
    ("N34", "echo hi | bash", main_repo, None),
    ("N35", "bash -c 'echo git checkout'", main_repo, None),
    ("N36", "taskset 0x3 ls", main_repo, None),
    ("N37", "script -qc 'ls' /dev/null", main_repo, None),
    ("N38", 'echo "$(git status)"', main_repo, None),
    ("N39", "echo '$(git stash)'", main_repo, None),
    ("N40", 'echo "cost is $5 and $(date)"', main_repo, None),
    ("N41", "tmux send-keys -t s:0 'ls' Enter", main_repo, None),
    ("N42", "git switch --force-create wt/x", main_repo, None),
    ("N43", "taskset 1 ls", main_repo, None),
    ("N44", "git checkout-index -a", main_repo, None),
    ("N45", 'git commit -m "tip: $(git rev-parse HEAD)"', main_repo, "ask"),
    # U-series: forms the hook docstring lists as NOT covered. They are expected to pass with no decision.
    # If one of these starts failing the hook got wider: update the docstring, README section 10 and the closeout.
    ("U01", "cat script.sh | bash", main_repo, None),
    ("U02", "bash < script.sh", main_repo, None),
    ("U03", "source script.sh", main_repo, None),
    ("U04", "g=git; $g checkout x", main_repo, None),
    ("U05", "python3 -c \"import os; os.system('git checkout x')\"", main_repo, None),
    ("U06", "env -S 'git checkout x'", main_repo, None),
    ("U07", "ssh host 'git checkout x'", main_repo, None),
    ("U08", "docker exec c git checkout x", main_repo, None),
    ("U09", "git config alias.x '!git checkout' && git x", main_repo, None),
    ("U10", "git read-tree --reset -u HEAD", main_repo, None),
    ("U11", "git merge wt/084-x", main_repo, None),
    ("U12", "git rebase main", main_repo, None),
    ("U13", "curl -s x | sh", main_repo, None),
]


def run_hook(cmd, cwd, transcript=None):
    payload = {"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd, "hook_event_name": "PreToolUse"}
    if transcript:
        payload["transcript_path"] = transcript
    env = dict(os.environ, HOME=scratch)  # keep the test log out of the real ~/.claude
    out = subprocess.run([sys.executable, "-I", os.path.join(HERE, "guard_git.py")], input=json.dumps(payload),
                         capture_output=True, text=True, env=env, timeout=20)
    if out.returncode != 0:
        return "ERROR:" + out.stderr.strip()[:200]
    if not out.stdout.strip():
        return None
    return json.loads(out.stdout)["hookSpecificOutput"]["permissionDecision"]



# --- chat approval of a plain commit (RAL 084 Q-42): the hook reads the session transcript ---------------------------------
import time as _time  # noqa: E402


def _iso(age_min):
    return _time.strftime("%Y-%m-%dT%H:%M:%S.000Z", _time.gmtime(_time.time() - age_min * 60))


def human(text, age=1):
    return {"type": "user", "origin": {"kind": "human"}, "timestamp": _iso(age),
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


def queued(text, age=1):
    return {"type": "attachment", "timestamp": _iso(age),
            "attachment": {"type": "queued_command", "prompt": [{"type": "text", "text": text}], "origin": {"kind": "human"}, "timestamp": _iso(age)}}


def tool_result(text, age=1):  # a file the agent read may contain the words "human" and "1,2,3 커밋"
    return {"type": "user", "toolUseResult": {}, "timestamp": _iso(age), "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": '"kind": "human" ' + text}]}}


def assistant(text, age=1):
    return {"type": "assistant", "timestamp": _iso(age), "message": {"role": "assistant", "content": [{"type": "text", "text": '"human" ' + text}]}}


def compact(text, age=1):
    return {"type": "user", "isCompactSummary": True, "timestamp": _iso(age), "message": {"role": "user", "content": '"kind": "human" ' + text}}


def peer(text, age=1):
    return {"type": "user", "origin": {"kind": "peer", "name": "other"}, "timestamp": _iso(age), "message": {"role": "user", "content": '"human" ' + text}}


def write_transcript(name, entries):
    path = os.path.join(scratch, name + ".jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    return path


def human_blocks(blocks, age=1):  # the IDE adds its own text block before the user's text
    return {"type": "user", "origin": {"kind": "human"}, "timestamp": _iso(age),
            "message": {"role": "user", "content": [{"type": "text", "text": b} for b in blocks]}}


IDE = "<ide_opened_file>The user opened the file /x/q_questions.md in the IDE. This may or may not be related.</ide_opened_file>"
PASTE = '\n\n<pasted_content id="0b87">\nusrg@host:~/repo$ ls\n</pasted_content id="0b87">\n\n'
GIT_COMMIT = "git commit -q -m x"
CHAT = [  # (id, command, transcript entries (None = no transcript_path, "missing" = unreadable path), expected decision)
    ("C01", GIT_COMMIT, [human("1,2,3 커밋")], None),
    ("C02", GIT_COMMIT, None, "ask"),
    ("C03", GIT_COMMIT, [human("다음으로 넘어가자")], "ask"),
    ("C04", GIT_COMMIT, [human("1,2,3 커밋", age=40)], "ask"),
    ("C05", GIT_COMMIT, [human("1,2,3 커밋", age=5), human("아, 커밋 하지 마", age=2)], "ask"),
    ("C06", GIT_COMMIT, [human("RAL 085 확인해줘\n1,2,3 커밋\n그리고 이름도 정하자")], None),
    ("C07", GIT_COMMIT, [tool_result("1,2,3 커밋")], "ask"),
    ("C08", GIT_COMMIT, [assistant("1,2,3 커밋")], "ask"),
    ("C09", GIT_COMMIT, [compact("1,2,3 커밋")], "ask"),
    ("C10", GIT_COMMIT, [peer("1,2,3 커밋")], "ask"),
    ("C11", GIT_COMMIT, [queued("1,2,3 커밋")], None),
    ("C12", "git commit --amend -m x", [human("1,2,3 커밋")], "ask"),
    ("C13", "git commit -am x", [human("1,2,3 커밋")], "ask"),
    ("C14", "git commit --all -m x", [human("1,2,3 커밋")], "ask"),
    ("C15", "git push origin main", [human("1,2,3 커밋")], "ask"),
    ("C16", "git add a && git commit -q -m x && git push", [human("1,2,3 커밋")], "ask"),
    ("C17", GIT_COMMIT, [human("커밋은 나중에 할게")], "ask"),
    ("C18", GIT_COMMIT, [human("커밋할까?")], "ask"),
    ("C19", GIT_COMMIT, [human("1,2,3 커밋", age=3), human("이제 다음 질문", age=1)], None),
    ("C20", 'git commit -q -m "-a fix"', [human("1,2,3 커밋")], None),
    ("C21", GIT_COMMIT, "missing", "ask"),
    ("C22", GIT_COMMIT, [human("commit all")], None),
    ("C23", GIT_COMMIT, [human("1만 커밋")], None),
    ("C24", GIT_COMMIT, [human("please commit it when you are ready")], "ask"),
    ("C25", GIT_COMMIT, [human("1,2,3 커밋", age=3), human("커밋 하지 마", age=1)], "ask"),
    ("C26", "git add a b && git commit -q -m x", [human("전부 커밋해줘")], None),
    ("C27", 'git commit -q -m "tip: $(git rev-parse HEAD)"', [human("1,2,3 커밋")], None),
    ("C28", "git commit -q -m x -- a b", [human("1,2,3 커밋")], None),
    ("C29", "git checkout -- .", [human("1,2,3 커밋")], "deny"),
    ("C30", "bash -c 'git commit -q -m x'", [human("1,2,3 커밋")], None),
    # a real message of 2026-10-17 had an IDE block, a paste block and the approval line in one text block
    ("C31", GIT_COMMIT, [human_blocks([IDE, PASTE + "1,2,3 커밋"])], None),
    ("C32", GIT_COMMIT, [human_blocks([IDE, '<pasted_content id="0b87">\n1,2,3 커밋\n</pasted_content id="0b87">'])], "ask"),
    ("C33", GIT_COMMIT, [human_blocks(['<pasted_content id="a1">\nfoo\n</pasted_content>\n1,2,3 커밋\n</pasted_content id="a1">'])], "ask"),
    ("C34", GIT_COMMIT, [human_blocks(["<ide_opened_file>1,2,3 커밋</ide_opened_file>", "다음으로 넘어가자"])], "ask"),
    ("C35", GIT_COMMIT, [human_blocks([IDE, "권고대로"])], "ask"),
    ("C36", GIT_COMMIT, [human_blocks([IDE, "1,2,3 커밋"])], None),
    # a real message of 2026-10-18 answered a numbered list item by item: "1. 1 커밋" (PAPER1 002, lesson L-023)
    ("C37", GIT_COMMIT, [human("1. 1 커밋\n2. 응\n3. 하지 않기\n4. 열자")], None),
    ("C38", GIT_COMMIT, [human("1) 커밋")], None),
    ("C39", GIT_COMMIT, [human("1. 1 진행\n2. 응")], "ask"),
    ("C40", GIT_COMMIT, [human("1. 1 커밋\n2. 아니 커밋 하지 마")], "ask"),
    ("C41", GIT_COMMIT, [human("1. 커밋할까?")], "ask"),
    ("C42", GIT_COMMIT, [human("2024. 커밋")], "ask"),
    # a real message of 2026-10-19 put another decision and the approval on one line (PAPER1 004, lesson L-023)
    ("C43", GIT_COMMIT, [human("1 종결, 1,2 커밋")], None),
    ("C44", GIT_COMMIT, [human("1 확인 / 2 커밋")], None),
    ("C45", GIT_COMMIT, [human("1 종결, commit all")], None),
    ("C46", GIT_COMMIT, [human("1 종결, 커밋은 하지 마")], "ask"),
    ("C47", GIT_COMMIT, [human("1 종결, 2 보류")], "ask"),
    ("C48", GIT_COMMIT, [human("1 종결, 1,2 커밋할까?")], "ask"),
    ("C49", GIT_COMMIT, [human("1 종결, 1,2 커밋 말고 나중에")], "ask"),
    ("C50", GIT_COMMIT, [human("1,2 커밋은 아직, 1 종결")], "ask"),
    # a real message of 2026-10-31 joined the other decision with a connective ending, no comma (PAPER1 006, lesson L-023)
    ("C51", GIT_COMMIT, [human("006 닫고 1,2 커밋")], None),
    ("C52", GIT_COMMIT, [human("리뷰 끝났으니 1 커밋")], None),
    ("C53", GIT_COMMIT, [human("확인해서 전부 커밋해줘")], None),
    ("C54", GIT_COMMIT, [human("확인하면 1,2 커밋")], "ask"),
    ("C55", GIT_COMMIT, [human("나중에 1,2 커밋")], "ask"),
    ("C56", GIT_COMMIT, [human("006 닫고 1,2 커밋할까?")], "ask"),
    ("C57", GIT_COMMIT, [human("006 닫고 커밋 하지 마")], "ask"),
    ("C58", GIT_COMMIT, [human("리뷰 끝나고 1 커밋")], "ask"),
    ("C59", GIT_COMMIT, [human("닫고 내일 커밋")], "ask"),
    ("C60", GIT_COMMIT, [human("1 종결 1,2 커밋")], "ask"),
    ("C61", GIT_COMMIT, [human("006 닫고 commit all")], None),
]
for cid, cmd, entries, want in CHAT:
    if entries is None:
        tp = None
    elif entries == "missing":
        tp = os.path.join(scratch, "no_such_transcript.jsonl")
    else:
        tp = write_transcript(cid, entries)
    CASES.append((cid, cmd, main_repo, want, tp))

rows, fails = [], 0
for case in CASES:
    cid, cmd, cwd, want = case[:4]
    got = run_hook(cmd, cwd, case[4] if len(case) > 4 else None)
    ok = got == want
    fails += not ok
    rows.append((cid, "PASS" if ok else "FAIL", str(want), str(got), cmd.replace("\n", "⏎")[:60]))

print(f"{len(CASES) - fails}/{len(CASES)} pass")
for r in rows:
    print(" | ".join(r))
sys.exit(1 if fails else 0)
