#!/usr/bin/env bash
# wait_job.sh — block until a run_job.sh job ends, then exit, so the harness wakes the session
# (RAL ticket 084, Q-23). Run it as a BACKGROUND command (run_in_background) in the same turn
# that launched the job. Never poll it, never wrap it in nohup or &.
#
#   wait_job.sh <job_dir> [--poll <seconds, default 15>] [--heartbeat <seconds>]
#
# Exit 0  the job ended and wrote DONE.json (its own exit code is printed, not returned)
# Exit 3  the job died without DONE.json (killed, reboot, OOM): treat as a failed run
# Exit 2  usage error or no job.json in <job_dir>
# While the user is away (launch.py away on) there is no heartbeat and an ending job is held until they are back.
# Exit 4  --heartbeat only: the job is still running after that many seconds. The exit wakes the session so it
#         can check on the job (job_status.sh) and start wait_job.sh again. The end-of-job wake alone never
#         announces a stuck or silent run (LESSONS RAL lesson L-014); a heartbeat of 300 gives a check every five minutes.
set -euo pipefail
dir="${1:?usage: wait_job.sh <job_dir> [--poll s] [--heartbeat s]}"; poll=15; beat=0; shift
while [ $# -gt 0 ]; do
  case "$1" in --poll) poll="${2:?}"; shift 2;; --heartbeat) beat="${2:?}"; shift 2;; *) echo "wait_job: unknown argument $1" >&2; exit 2;; esac
done
[ -f "$dir/job.json" ] || { echo "wait_job: no job.json in $dir" >&2; exit 2; }
summary() {
  python3 - "$dir" "$1" <<'EOF'
import json, os, sys
d, state = sys.argv[1], sys.argv[2]
j = json.load(open(os.path.join(d, "job.json")))
done = json.load(open(os.path.join(d, "DONE.json"))) if os.path.exists(os.path.join(d, "DONE.json")) else {}
print(f"JOB {state}: {j['id']}  started {j['started']}  "
      + (f"ended {done['ended']}  exit_code {done['exit_code']}  duration {done['duration_s']} s" if done else "no DONE.json"))
print(f"next step recorded at launch: {j.get('next') or '(none)'}")
print(f"log: {os.path.join(d, j.get('log', 'job.log'))}")
print(f"after acting on it: qrispy job handled {d} \"<what was done>\"")
EOF
}
# The user is away (`qrispy worker away on`, RAL ticket 087 Q-16): no heartbeat, and a job that ends is kept
# for the return summary; the waiter exits only once the user is back.
LAUNCH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../launch.py"
away_active() { [ -f "$LAUNCH" ] && python3 -I "$LAUNCH" away active >/dev/null 2>&1; }
hold_while_away() {
  if away_active; then
    python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import launch; launch.away_event(sys.argv[2])' "$(dirname "$LAUNCH")" "$1"
    while away_active; do sleep "$poll"; done
    echo "the user is back (launch.py away off)"
  fi
}
for _ in $(seq 1 40); do [ -f "$dir/pid" ] || [ -f "$dir/DONE.json" ] && break; sleep 0.5; done
t0=$SECONDS
while :; do
  if [ -f "$dir/DONE.json" ]; then hold_while_away "job $(basename "$dir") ended"; summary ENDED; exit 0; fi
  if [ "$beat" -gt 0 ] && away_active; then t0=$SECONDS; fi
  if [ "$beat" -gt 0 ] && [ $((SECONDS - t0)) -ge "$beat" ]; then
    echo "JOB STILL RUNNING after $((SECONDS - t0)) s: $dir"; echo "check it: qrispy job status $dir [stream or output file]; then start qrispy job wait again with --heartbeat $beat"; exit 4
  fi
  p="$(cat "$dir/pid" 2>/dev/null || true)"
  if [ -z "$p" ] || ! ps -p "$p" >/dev/null 2>&1; then  # ps, not /proc: macOS has no /proc (RAL ticket 089)
    sleep 2; [ -f "$dir/DONE.json" ] && { hold_while_away "job $(basename "$dir") ended"; summary ENDED; exit 0; }   # it may have just finished
    hold_while_away "job $(basename "$dir") DIED without DONE.json"; summary DIED; exit 3
  fi
  nap="$poll"
  if [ "$beat" -gt 0 ]; then left=$((beat - (SECONDS - t0))); [ "$left" -lt 1 ] && left=1; [ "$left" -lt "$nap" ] && nap="$left"; fi
  sleep "$nap"
done
