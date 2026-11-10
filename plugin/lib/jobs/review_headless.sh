#!/usr/bin/env bash
# review_headless.sh — run one QRISPY review round in a separate headless Opus session
# (RAL ticket 084, Q-36 and Q-38). It does the mechanical steps of the qrispy:review skill and
# nothing that needs judgment: it never writes a response, a lesson or state.json.
#
#   review_headless.sh start  <SYSTEM-NNN-slug> <round> [--dry-run]
#       freeze the hashes the reviewer must not change, write the prompt and run script, launch the
#       reviewer as a tracked job (`qrispy job run`). --dry-run prints and changes nothing.
#   review_headless.sh finish <SYSTEM-NNN-slug> <round>
#       after the job ended: pull the review text out of the stream, check it (husk, attestation hashes,
#       guard diff), save it verbatim as tickets/<slug>/rev<round>.md, keep the run as evidence.
#   review_headless.sh freeze <SYSTEM-NNN-slug> <round>
#   review_headless.sh record <SYSTEM-NNN-slug> <round> <text_file>
#       the subagent route (PAPER1 ticket 001, 2026-10-18): freeze the same hashes before calling the
#       qrispy:reviewer agent (plugin/agents/reviewer.md, Opus, effort high) through the Agent tool;
#       after it returns, run record with either its final message saved unchanged or the Agent tool's output
#       file (the subagent transcript; record takes the SubagentHandback message from it), which does the
#       same checks as finish and saves it verbatim. The subagent does not appear as a separate session.
#
# While a round runs, do not edit anything inside tickets/<slug>/ or tickets/*.md: the guard check
# compares them, and a difference inside the ticket directory discards the round.
# The reviewer is read-only and reads only the repository (see REVIEW_PROMPT.md); this session's own
# conversation is not visible to it.
#
# Environment: REVIEW_MODEL (default claude-opus-5-5), REVIEW_EXTRA_DIRS (space separated, extra read dirs).
# Exit codes of finish: 0 saved, 2 job not finished or failed, 3 round discarded (ticket directory changed),
# 4 no usable review text, 5 husk, 6 attestation hashes do not match the files on disk.
set -euo pipefail
die() { echo "review_headless: $1" >&2; exit "${2:-1}"; }
mode="${1:-}"; slug="${2:-}"; round="${3:-}"; flag="${4:-}"
[ -n "$mode" ] && [ -n "$slug" ] && [ -n "$round" ] || die "usage: qrispy review freeze|record|start|finish <SYSTEM-NNN-slug | <root>/SYSTEM-NNN-slug> <round> [<text_file> (record) | --dry-run (start)]"
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # the kit's tools; the repository is found from the working folder (RAL ticket 090)
conf() { python3 -B "$LIB/qrispy_config.py" "$@"; }
REPO=$(conf repo 2>&1) || die "${REPO#qrispy_config: }"
cd "$REPO"
# a real command for xargs (it cannot call a shell function), in the "hash  path" format the discard check reads; never BSD
# /sbin/sha256, whose "SHA256 (path) = hash" lines hid ticket paths from that check (RAL ticket 090, found by the Linux run)
if command -v sha256sum >/dev/null 2>&1; then SHA=(sha256sum); else SHA=(shasum -a 256); fi
# Ticket systems come from qrispy.json (RAL ticket 089). A primary-system (here RAL) ticket is named by its slug; a ticket of
# another system by its path, e.g. side/tickets/001-planning (PAPER1 ticket 001, 2026-10-17).
T=$(conf ticket-dir "$slug" 2>&1) || die "${T#qrispy_config: }"   # its reason: a bad slug, or no/malformed qrispy.json (RAL ticket 089 rev1 A1-3)
P=$(conf primary-root)                         # its *.md files are the shared method documents
SCR=$(conf review-scratch)
[[ "$round" =~ ^[0-9]+$ ]] && [ "$round" -ge 1 ] || die "bad round: $round"
[ -d "$T" ] || die "no such ticket directory: $T"
# The deliverable named in state.json is frozen too when it is one existing file (it often lives outside the
# ticket directory, as a project's ROADMAP.md does); a change to it discards the round.
DELIV=$(python3 -c "import json,os,sys; d=json.load(open(sys.argv[1])).get('deliverable') or ''; print(d if os.path.isfile(d) else '')" "$T/state.json" 2>/dev/null || true)
S="$SCR/$slug/rev$round"          # the reviewer prompt names this scratch directory
J="$S/job"
MODEL="${REVIEW_MODEL:-claude-opus-5-5}"
ALLOWED='Read Grep Glob Bash(sha256sum:*) Bash(shasum:*) Bash(qrispy config:*) Bash(ls:*) Bash(cat:*) Bash(python3:*) Bash(find:*) Bash(wc:*) Bash(diff:*) Bash(grep:*) Bash(head:*) Bash(tail:*) Bash(mkdir:*) Bash(date:*) Bash(stat:*) Bash(readlink:*) Bash(cmp:*) Bash(git status:*) Bash(git log:*) Bash(git diff:*) Bash(git show:*) Bash(git worktree list:*) Bash(git branch:*)'
DIRS="$HOME/.claude $SCR $(dirname "$LIB") ${REVIEW_EXTRA_DIRS:-}"   # + the plugin: the reviewer reads the kit method files
while read -r x; do if [ -n "$x" ] && [ -d "$x" ]; then DIRS="$DIRS $x"; fi; done < <(conf external-roots)  # other repositories' tickets (MASF)

snapshot() { { find "$T" -type f ! -name "rev${round}.md"; ls "$P"/*.md "$(dirname "$LIB")"/method/*.md; if [ -n "$DELIV" ]; then echo "$DELIV"; fi; } | LC_ALL=C sort | xargs "${SHA[@]}"; }  # + the kit's method files the reviewer reads (RAL ticket 090)
prompt_text() {
  echo "TICKET=$slug ROUND=$round"   # the session runs as the reviewer agent itself (--agent below); the fork skill is gone (RAL ticket 090 Q-5)
}
run_script_text() {
  echo '#!/usr/bin/env bash'
  echo "cd $REPO"
  echo "claude -p \"\$(cat $S/prompt.txt)\" --agent qrispy:reviewer --model $MODEL --permission-mode default --disallowedTools \"Edit Write NotebookEdit\" --allowedTools \"$ALLOWED\" --add-dir $DIRS --output-format stream-json --verbose > $S/stream.jsonl 2> $S/err.txt"
}

verify_and_save() {   # checks 2-4b, then saves the text verbatim as rev<round>.md (shared by finish and record)
  local R="$1"
  # 2. husk check (the skill: it must start with the protocol block and carry real substance)
  if ! head -c 40 "$R" | grep -q "QRISPY-REVIEW-PROTOCOL" || ! grep -q "QRISPY-REVIEW-META" "$R" || [ "$(wc -c < "$R")" -lt 4000 ]; then
    cp "$R" "$S/rev$round.husk.md"; die "the returned text is a husk (no protocol block, no META block, or under 4 kB); kept as $S/rev$round.husk.md. Rerun, never pad it." 5
  fi
  # 3. attestation: the three hashes in the protocol block must match the files on disk now
  stale=$(python3 - "$R" "$(dirname "$LIB")" <<'PY'
import hashlib, os, re, sys
txt = open(sys.argv[1]).read()
block = txt.split("-->", 1)[0]
found = dict(re.findall(r"^(\S+): ([0-9a-f]{64})$", block, re.M))
bad = [k + "(missing)" for k in ("method/QRISPY_METHOD.md", "method/DEV_REVIEW_RECIPE.md", "AGENTS.md") if k not in found]  # REVIEW_PROMPT: a missing entry fails too (RAL ticket 090)
for path, h in found.items():
    real = os.path.join(sys.argv[2], path) if path.startswith("method/") else path  # kit method files live in the plugin (RAL ticket 090)
    try:
        cur = hashlib.sha256(open(real, "rb").read()).hexdigest()
    except OSError:
        cur = "missing"
    if cur != h:
        bad.append(path)
print(" ".join(bad))
PY
)
  if [ -n "$stale" ]; then cp "$R" "$S/rev$round.stale_attestation.md"; die "attestation hashes do not match the files now: $stale (kept as $S/rev$round.stale_attestation.md)" 6; fi
  # 4. guard check: nothing inside the ticket directory may have changed
  snapshot > "$S/guard_after.txt"
  if ! diff -q "$S/guard_before.txt" "$S/guard_after.txt" >/dev/null; then
    diff "$S/guard_before.txt" "$S/guard_after.txt" > "$S/guard_diff.txt" || true
    if grep -q " $T/" "$S/guard_diff.txt" || { [ -n "$DELIV" ] && grep -qF " $DELIV" "$S/guard_diff.txt"; }; then
      cp "$R" "$S/rev$round.discarded.md"
      cat "$S/guard_diff.txt"; die "a file inside $T (or the deliverable ${DELIV:-none}) changed during the round: the round is discarded (text kept as $S/rev$round.discarded.md)" 3
    fi
    echo "WARNING: shared $P/*.md files changed during the round (usually another session; check the times, then say so in the response):"
    grep -o "$P/[A-Za-z0-9_./-]*\.md" "$S/guard_diff.txt" | sort -u | while read -r f; do python3 -c 'import os,sys,time; print("  " + time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(sys.argv[1]))) + "  " + sys.argv[1])' "$f"; done  # was GNU-only `ls --time-style` (RAL ticket 089)
  fi
  # 4b. working-tree status outside the ticket directory (warn only: other sessions also edit this tree, and the
  #     headless reviewer may run python3, which the git hook cannot see into)
  if [ -f "$S/status_before.txt" ]; then
    git status --porcelain=v1 -uall 2>/dev/null | LC_ALL=C sort > "$S/status_after.txt" || true
    if ! diff -q <(LC_ALL=C sort "$S/status_before.txt") "$S/status_after.txt" >/dev/null; then  # re-sort: a freeze made by an older script may use another locale's order (RAL ticket 089 rev3)
      echo "NOTE: git working-tree status changed during the round (other sessions, or the reviewer itself). Entries outside $T/:"
      diff <(LC_ALL=C sort "$S/status_before.txt") "$S/status_after.txt" | grep '^[<>]' | grep -v " $T/" | head -15 || true
    fi
  fi
  cp "$R" "$T/rev$round.md"; cmp "$R" "$T/rev$round.md"
}

case "$mode" in
start)
  [ ! -e "$T/rev$round.md" ] || die "$T/rev$round.md already exists"
  [ ! -e "$J/job.json" ] || die "a job for this round already exists: $J (inspect it with qrispy job status)"
  if [ "$flag" = "--dry-run" ]; then
    echo "# dry run: nothing is written or launched"
    echo "ticket $T, round $round, model $MODEL, scratch $S"
    echo "deliverable frozen: ${DELIV:-none}"
    echo "files to freeze: $(snapshot | wc -l)"
    echo "--- prompt"; prompt_text; echo "--- run script"; run_script_text
    exit 0
  fi
  mkdir -p "$S"
  snapshot > "$S/guard_before.txt"
  git status --porcelain=v1 -uall 2>/dev/null | LC_ALL=C sort > "$S/status_before.txt" || true
  prompt_text > "$S/prompt.txt"
  run_script_text > "$S/run.sh"; chmod +x "$S/run.sh"
  echo "frozen $(wc -l < "$S/guard_before.txt") file hashes at $(date '+%H:%M:%S')"
  "$LIB/jobs/run_job.sh" "$J" --next "qrispy review finish $slug $round" -- "$S/run.sh"
  echo "expected duration: 10 to 20 minutes (earlier rounds took 10 and 16). Check progress about every 5 minutes with:"
  echo "  qrispy job status $J $S/stream.jsonl"
  echo "Start the waiter with a heartbeat so you are woken every five minutes to check: qrispy job wait $J --heartbeat 300 (it exits with code 4 and a status line; check with job_status.sh, then start it again)."
  echo "Do not edit $T/ or $P/*.md until the job ends. When it ends, run: qrispy review finish $slug $round"
  ;;
finish)
  [ -f "$J/job.json" ] || die "no job for this round; run start first" 2
  if [ ! -f "$J/DONE.json" ]; then
    "$LIB/jobs/job_status.sh" "$J" "$S/stream.jsonl" || true
    die "the job has not finished (or died without DONE.json)" 2
  fi
  code=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['exit_code'])" "$J/DONE.json")
  [ "$code" = "0" ] || { tail -5 "$S/err.txt" 2>/dev/null || true; die "the reviewer session exited with code $code" 2; }
  # 1. pull the review text and the run statistics out of the stream
  python3 - "$S/stream.jsonl" "$S/review_text.md" "$S/stats.txt" <<'PY' || die "no usable result in the stream" 4
import json, sys
calls, res = 0, None
for line in open(sys.argv[1], errors="replace"):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    if e.get("type") == "assistant":
        calls += sum(1 for c in e["message"]["content"] if c.get("type") == "tool_use")
    if e.get("type") == "result":
        res = e
if not res or res.get("subtype") != "success" or not res.get("result"):
    sys.exit(1)
open(sys.argv[2], "w").write(res["result"])
open(sys.argv[3], "w").write("tool_calls=%d turns=%s cost_usd=%.2f denials=%d\n" % (calls, res.get("num_turns"), res.get("total_cost_usd") or 0, len(res.get("permission_denials") or [])))
PY
  R="$S/review_text.md"
  verify_and_save "$R"
  # 5. keep the run as evidence
  E="$T/evidence/review_runs/rev$round"; mkdir -p "$E"
  cp "$S/prompt.txt" "$S/run.sh" "$S/stream.jsonl" "$E/"; [ ! -s "$S/err.txt" ] || cp "$S/err.txt" "$E/"
  "$LIB/jobs/run_job.sh" --handled "$J" "saved $T/rev$round.md and the run under $E" >/dev/null
  # 6. report; the judgment steps stay with the worker
  echo "saved $T/rev$round.md ($(wc -c < "$T/rev$round.md") bytes), verbatim"
  grep -E "^(verdict|blocking_open|advisory_open):" "$R" | tr '\n' ' '; echo
  python3 -c "import json,sys;d=json.load(open(sys.argv[1]));print('duration_s',d['duration_s'])" "$J/DONE.json"
  cat "$S/stats.txt"
  echo "still to do by hand: register the round in state.json.reviews, write rev${round}_response.md (every finding accepted or rejected), put your own mistakes into $P/LESSONS.md"
  ;;
freeze)
  [ ! -e "$T/rev$round.md" ] || die "$T/rev$round.md already exists"
  [ ! -e "$S/guard_before.txt" ] || die "this round is already frozen: $S (remove the scratch directory to start over)"
  mkdir -p "$S"
  snapshot > "$S/guard_before.txt"
  git status --porcelain=v1 -uall 2>/dev/null | LC_ALL=C sort > "$S/status_before.txt" || true
  echo "subagent $(date '+%F %T')" > "$S/route.txt"
  echo "frozen $(wc -l < "$S/guard_before.txt") file hashes at $(date '+%H:%M:%S'); deliverable frozen: ${DELIV:-none}"
  echo "now call the Agent tool: subagent_type qrispy:reviewer, prompt exactly: TICKET=$slug ROUND=$round"
  echo "do not edit $T/, ${DELIV:-the deliverable} or $P/*.md until it returns; then save its final message unchanged and run:"
  echo "  qrispy review record $slug $round <file with the returned text>"
  ;;
record)
  txt="$flag"; [ -n "$txt" ] && [ -f "$txt" ] || die "usage: review_headless.sh record <ticket> <round> <text_file>"
  [ -f "$S/guard_before.txt" ] || die "no frozen hashes for this round; run freeze first"
  [ ! -e "$T/rev$round.md" ] || die "$T/rev$round.md already exists"
  # The text may be the subagent transcript itself (JSONL, the Agent tool's output file): then take the
  # message of its SubagentHandback call, which is the final report unindented (PAPER1 ticket 001 rev2, 2026-10-18).
  python3 - "$txt" "$S/review_text.md" <<'PY' || die "could not read the review text from $txt" 4
import json, sys
src, out = sys.argv[1], sys.argv[2]
raw = open(src, errors="replace").read()
first = raw.lstrip()[:1]
if first != "{":
    open(out, "w").write(raw); sys.exit(0)
msg = None
for line in raw.splitlines():
    try:
        e = json.loads(line)
    except ValueError:
        continue
    c = (e.get("message") or {}).get("content")
    if isinstance(c, list):
        for x in c:
            if x.get("type") == "tool_use" and x.get("name") == "SubagentHandback":
                msg = x["input"].get("message")
if not msg:
    sys.exit(1)
open(out, "w").write(msg)
PY
  verify_and_save "$S/review_text.md"
  E="$T/evidence/review_runs/rev$round"; mkdir -p "$E"
  cp "$S/route.txt" "$E/" 2>/dev/null || true
  echo "TICKET=$slug ROUND=$round" > "$E/prompt.txt"
  echo "saved $T/rev$round.md ($(wc -c < "$T/rev$round.md") bytes), verbatim (subagent route)"
  grep -E "^(verdict|blocking_open|advisory_open):" "$S/review_text.md" | tr '\n' ' '; echo
  echo "still to do by hand: register the round in state.json.reviews, write rev${round}_response.md (every finding accepted or rejected), put your own mistakes into $P/LESSONS.md"
  ;;
*) die "unknown mode: $mode (start, finish, freeze or record)" ;;
esac
