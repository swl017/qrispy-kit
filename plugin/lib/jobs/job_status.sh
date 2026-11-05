#!/usr/bin/env bash
# job_status.sh — one-screen progress check of a run_job.sh job (RAL ticket 084, RAL lesson L-014).
# A job's END wakes the session, but a stuck, silent or wrongly configured job never ends,
# so check on it while it runs. Read-only.
#
#   job_status.sh <job_dir> [watched_file ...]
#
# Prints: running or ended, elapsed time, the last lines of job.log, and for job.log and every
# watched file (a stream file, an output CSV, a results folder) its size and how long ago it last
# changed. A file silent for many minutes while the process is alive is the sign of a stall.
set -uo pipefail
dir="${1:?usage: job_status.sh <job_dir> [watched_file ...]}"; shift || true
[ -f "$dir/job.json" ] || { echo "job_status: no job.json in $dir" >&2; exit 2; }
python3 - "$dir" "$@" <<'EOF'
import datetime, json, os, sys, time
d, watched = sys.argv[1], sys.argv[2:]
j = json.load(open(os.path.join(d, "job.json")))
now = datetime.datetime.now().astimezone()
start = datetime.datetime.fromisoformat(j["started"]) if j.get("started") else None  # empty in jobs started on macOS before RAL ticket 089
done = os.path.join(d, "DONE.json")
pid = open(os.path.join(d, "pid")).read().strip() if os.path.exists(os.path.join(d, "pid")) else ""
def pid_alive(p):  # os.kill(pid, 0), not /proc: macOS has no /proc (RAL ticket 089)
    try:
        if int(p) <= 0:
            return False
        os.kill(int(p), 0)
        return True
    except PermissionError:
        return True
    except (OSError, ValueError, OverflowError):
        return False
alive = bool(pid) and pid_alive(pid)
if os.path.exists(done):
    x = json.load(open(done))
    print(f"ENDED  {j['id']}  exit_code {x['exit_code']}  signal {x.get('signal') or '-'}  duration {x['duration_s']} s")
elif alive:
    print(f"RUNNING  {j['id']}  pid {pid}  elapsed {int((now - start).total_seconds()) if start else '?'} s  (now {now:%H:%M:%S})")
else:
    print(f"DIED  {j['id']}: no DONE.json and the process is gone (killed, reboot, OOM)")
def age(p):
    try:
        s = os.stat(p)
    except OSError:
        return f"{p}: missing"
    return f"{p}: {s.st_size} bytes, last changed {int(time.time() - s.st_mtime)} s ago"
log = os.path.join(d, j.get("log", "job.log"))
for p in [log] + watched:
    print(age(p))
if os.path.exists(log):
    tail = open(log, errors="replace").read().splitlines()[-6:]
    print("--- job.log (last lines)" if tail else "--- job.log is empty")
    for t in tail:
        print("  " + t[:200])
EOF
