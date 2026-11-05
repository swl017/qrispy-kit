#!/usr/bin/env bash
# run_job.sh — launch a long job so that its END can wake the agent session (RAL ticket 084, Q-23).
#
#   run_job.sh <job_dir> [--next "<what to do when it ends>"] [--foreground] [--gpu sim|train|other] [--go "<ticket> Q-n"] -- <command> [args...]
#   run_job.sh --handled <job_dir> "<what was done with the result>"
#
# The job writes three files into <job_dir>:
#   job.json      at start: command, cwd, start time, pid, the --next step
#   DONE.json     at the end, success or failure: exit code, end time, duration
#   job.log       stdout + stderr (not tracked by git)
# and the agent adds HANDLED.json once it has acted on the result (--handled).
#
# Default mode detaches (setsid nohup, stdin closed): the job survives the agent session,
# the SSH link and the terminal (RAL ticket 084, its simulator recipe §5.x). --foreground runs it in the
# current shell instead, for a command sent into a tmux pane where tmux already keeps it alive.
#
# Detaching means the launch command returns at once, so the harness cannot see the end.
# In the SAME turn, start  qrispy job wait <job_dir>  as a background command:
# it exits when DONE.json appears (or the job dies), which is what wakes the session.
# Put the job dir under the ticket — tickets/<NNN-slug>/jobs/<id>/ — so `qrispy inbox` sees it.
#
# --gpu <kind> (RAL ticket 087 S2): take the machine's GPU lock (`qrispy lock`, lib/gpu_lock.py) before starting, as the
# job dir's ticket and that ticket's state.json session. If another owner holds it, nothing starts (exit 3): ask the user.
# When the job ends the lock goes back to `held` (the sim may still be up); release it with gpu_lock.py when done.
# --go "<ticket> Q-n" records which scoped go (state.json.go_scopes, RAL ticket 087 Q-7) this run relies on, in job.json.
set -euo pipefail

die() { printf 'run_job: %s\n' "$*" >&2; exit 2; }
now() { python3 -c 'import datetime; print(datetime.datetime.now().astimezone().isoformat(timespec="seconds"))'; }  # = GNU `date -Is`; BSD date has no -Is (RAL ticket 089)
alive() { [ -n "$1" ] && ps -p "$1" >/dev/null 2>&1; }  # /proc does not exist on macOS (RAL ticket 089)
json_str() { python3 -c 'import json,sys; print(json.dumps(sys.argv[1]))' "$1"; }

if [ "${1:-}" = "--handled" ]; then
  dir="${2:?job dir}"; note="${3:?what was done}"
  if [ ! -f "$dir/DONE.json" ]; then
    p="$(cat "$dir/pid" 2>/dev/null || true)"
    alive "$p" && die "$dir is still running (pid $p)"
  fi  # a job that died without DONE.json can be marked handled too
  tmp="$(mktemp "$dir/.handled.XXXXXX")"
  printf '{"handled": %s, "note": %s}\n' "$(json_str "$(now)")" "$(json_str "$note")" > "$tmp"
  mv -f "$tmp" "$dir/HANDLED.json"; echo "handled: $dir"; exit 0
fi

if [ "${1:-}" = "--inner" ]; then  # internal: runs detached, owns DONE.json
  dir="$2"; shift 2; [ "$1" = "--" ] && shift
  echo $$ > "$dir/pid"
  start=$(date +%s); got_signal=""
  "$@" & child=$!
  # Forward TERM/INT/HUP to the whole job, so killing the job leaves no orphans recording for hours
  # (RAL ticket 084, its simulator recipe §10.o). Detached, this shell leads its own process group.
  forward() {
    got_signal="$1"; trap '' TERM INT HUP
    if [ "$(ps -o pgid= -p $$ | tr -d ' ')" = "$$" ]; then kill -"$1" -- -$$ 2>/dev/null; else kill -"$1" "$child" 2>/dev/null; fi
  }
  trap 'forward TERM' TERM; trap 'forward INT' INT; trap 'forward HUP' HUP
  set +e
  while :; do wait "$child"; rc=$?; kill -0 "$child" 2>/dev/null || break; done
  set -e
  tmp="$(mktemp "$dir/.done.XXXXXX")"
  printf '{"exit_code": %d, "signal": %s, "ended": %s, "duration_s": %d}\n' "$rc" "$(json_str "$got_signal")" "$(json_str "$(now)")" "$(( $(date +%s) - start ))" > "$tmp"
  mv -f "$tmp" "$dir/DONE.json"   # atomic: a watcher never sees a half-written file
  if [ -n "${RUN_JOB_GPU:-}" ]; then  # back to held: the owner may keep the sim up for the next run (RAL ticket 087)
    python3 -I "$(dirname "$0")/../gpu_lock.py" hold --job "$dir" >/dev/null 2>&1 || true
  fi
  exit "$rc"
fi

dir="${1:?usage: run_job.sh <job_dir> [--next ...] [--foreground] -- <command>}"; shift
next=""; fg=0; gpu=""; go=""
while [ $# -gt 0 ] && [ "$1" != "--" ]; do
  case "$1" in
    --next) next="$2"; shift 2 ;;
    --foreground) fg=1; shift ;;
    --gpu) gpu="$2"; shift 2 ;;
    --go) go="$2"; shift 2 ;;
    *) die "unknown option $1 (put the command after --)" ;;
  esac
done
[ "${1:-}" = "--" ] || die "missing -- before the command"; shift
[ $# -gt 0 ] || die "no command given"
mkdir -p "$dir"; dir="$(cd "$dir" && pwd)"
if [ -f "$dir/job.json" ] && [ ! -f "$dir/DONE.json" ]; then
  p="$(cat "$dir/pid" 2>/dev/null || true)"
  alive "$p" && die "$dir already has a running job (pid $p)"
  die "$dir has a job.json without DONE.json: an earlier job died; use a new job dir"
fi
if [ -n "$gpu" ]; then  # take the GPU lock first: a refused take leaves no half-started job behind
  python3 -I "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../gpu_lock.py" take --kind "$gpu" --job "$dir" --note "job $(basename "$dir")" >/dev/null || exit $?
fi
export RUN_JOB_GPU="$gpu"
rm -f "$dir/DONE.json" "$dir/HANDLED.json" "$dir/pid"
cmd_json="$(python3 -c 'import json,sys; print(json.dumps(sys.argv[1:]))' "$@")"
printf '{"id": %s, "command": %s, "cwd": %s, "started": %s, "host": %s, "mode": %s, "next": %s, "gpu": %s, "go": %s, "log": "job.log"}\n' \
  "$(json_str "$(basename "$dir")")" "$cmd_json" "$(json_str "$PWD")" "$(json_str "$(now)")" \
  "$(json_str "$(hostname)")" "$(json_str "$([ $fg -eq 1 ] && echo foreground || echo detached)")" \
  "$(json_str "$next")" "$(json_str "$gpu")" "$(json_str "$go")" > "$dir/job.json"

self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
if [ $fg -eq 1 ]; then
  set +e; "$self" --inner "$dir" -- "$@" 2>&1 | tee -a "$dir/job.log"; rc=${PIPESTATUS[0]}; exit "$rc"
fi
if command -v setsid >/dev/null 2>&1; then detach=(setsid); else  # macOS has no setsid(1): the same call from Python, keeping the pid (RAL ticket 089)
  detach=(python3 -c 'import os, sys; os.setsid(); os.execvp(sys.argv[1], sys.argv[1:])'); fi
"${detach[@]}" nohup "$self" --inner "$dir" -- "$@" >> "$dir/job.log" 2>&1 < /dev/null &
launcher=$!   # setsid and its Python stand-in exec in place: this is the job's pid once it runs
for _ in 1 2 3 4 5 6 7 8 9 10; do [ -f "$dir/pid" ] && break; sleep 0.2; done
if [ ! -f "$dir/pid" ] && [ ! -f "$dir/DONE.json" ]; then  # say so instead of printing "started … (pid ?)" (RAL ticket 089)
  if kill -0 "$launcher" 2>/dev/null; then   # slow to start (a loaded machine): not a failure (RAL ticket 089 rev1 A1-4)
    echo "run_job: no pid file after 2 s; $(basename "$dir") may still be starting (pid $launcher): check it with qrispy job status" >&2
  else
    echo "run_job: $(basename "$dir") did not start; job.log:" >&2; tail -5 "$dir/job.log" >&2
    if [ -n "$gpu" ]; then  # back to held, as at a normal end: the lock must not stay `running` for a dead job (RAL ticket 089 rev2 A2-3)
      python3 -I "$(dirname "$self")/../gpu_lock.py" hold --job "$dir" --note "job $(basename "$dir") did not start" >/dev/null 2>&1 || true
    fi
    exit 2
  fi
fi
printf 'started %s (pid %s) at %s\nnow start, as a background command in this same turn:\n  %s/wait_job.sh %s\n' \
  "$(basename "$dir")" "$(cat "$dir/pid" 2>/dev/null || echo '?')" "$(date +%H:%M:%S)" "$(dirname "$self")" "$dir"
