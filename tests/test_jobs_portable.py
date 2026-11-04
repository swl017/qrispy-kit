#!/usr/bin/env python3
"""Tests for run_job.sh, wait_job.sh and job_status.sh on any POSIX machine, including macOS, which has no setsid(1),
no `date -Is` and no /proc (RAL ticket 089 S3; before it, run_job.sh started nothing on macOS and printed
"started … (pid ?)"). Run from the kit: python3 -I tests/test_jobs_portable.py   (about 25 s, no GPU; RAL 090 moved it)"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
LIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugin", "lib")  # the kit's tools (RAL 090)
HERE = os.path.join(LIB, "jobs")
sys.path.insert(0, LIB)
import qrispy_config as qc  # noqa: E402

RUN, WAIT, STATUS = (os.path.join(HERE, n) for n in ("run_job.sh", "wait_job.sh", "job_status.sh"))
SCRATCH = tempfile.mkdtemp(prefix="jobs_portable_test_")
ENV = dict(os.environ, AGENT_LOCK_DIR=os.path.join(SCRATCH, "locks"))  # never the user's real away state or GPU lock
ENV.pop("QRISPY_REPO", None)
with open(os.path.join(SCRATCH, "qrispy.json"), "w") as _f:  # job dirs live here; gpu_lock finds the repository from them (RAL 090)
    json.dump({"systems": [{"name": "RAL", "root": "tickets"}], "review_scratch": os.path.join(SCRATCH, "review")}, _f)
ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d$")  # what GNU `date -Is` prints


def sh(*cmd, timeout=60):
    p = subprocess.run(list(cmd), capture_output=True, text=True, env=ENV, timeout=timeout)
    return p.returncode, p.stdout + p.stderr


def until(cond, secs=10.0):
    end = time.time() + secs
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.1)
    return False


def test_j1_job_starts_ends_and_wakes():
    d = os.path.join(SCRATCH, "j1")
    rc, out = sh(RUN, d, "--next", "nothing", "--", "python3", "-c", "import time; time.sleep(2); print('hello')")
    assert rc == 0 and re.search(r"started j1 \(pid \d+\)", out), out
    j = json.load(open(os.path.join(d, "job.json")))
    assert ISO.match(j["started"]), j["started"]
    rc, out = sh(STATUS, d)
    assert rc == 0 and out.startswith("RUNNING  j1"), out
    rc, out = sh(WAIT, d, "--poll", "1")
    assert rc == 0 and "JOB ENDED: j1" in out and "exit_code 0" in out, out
    done = json.load(open(os.path.join(d, "DONE.json")))
    assert done["exit_code"] == 0 and ISO.match(done["ended"]), done
    assert "hello" in open(os.path.join(d, "job.log")).read()


def test_j2_heartbeat_while_running():
    d = os.path.join(SCRATCH, "j2")
    sh(RUN, d, "--", "sleep", "6")
    rc, out = sh(WAIT, d, "--poll", "1", "--heartbeat", "2")
    assert rc == 4 and "JOB STILL RUNNING" in out, (rc, out)  # alive is seen as alive, not as DIED
    rc, out = sh(RUN, "--handled", d, "x")
    assert rc == 2 and "still running" in out, out
    rc, out = sh(RUN, d, "--", "true")
    assert rc == 2 and "already has a running job" in out, out
    os.kill(int(open(os.path.join(d, "pid")).read()), signal.SIGTERM)
    assert until(lambda: os.path.exists(os.path.join(d, "DONE.json")))


def test_j3_term_reaches_the_whole_job():
    """The detached shell must lead its own process group (setsid, or its Python stand-in on macOS), so TERM is
    forwarded to the group and leaves no orphan."""
    d = os.path.join(SCRATCH, "j3")
    marker = f"jobs-portable-{os.getpid()}"
    sh(RUN, d, "--", "bash", "-c", f"sleep 30 & wait  # {marker}")
    pid = int(open(os.path.join(d, "pid")).read())
    pgid = os.getpgid(pid)
    assert pgid == pid and os.getsid(pid) == pid, (pid, pgid, os.getsid(pid))
    os.kill(pid, signal.SIGTERM)
    assert until(lambda: os.path.exists(os.path.join(d, "DONE.json")))
    done = json.load(open(os.path.join(d, "DONE.json")))
    assert done["signal"] == "TERM", done
    left = subprocess.run(["pgrep", "-g", str(pgid)], capture_output=True, text=True).stdout.split()
    assert until(lambda: not subprocess.run(["pgrep", "-g", str(pgid)], capture_output=True, text=True).stdout.split(), 5), left


def test_j4_died_without_done():
    d = os.path.join(SCRATCH, "j4")
    os.makedirs(d)
    p = subprocess.Popen(["true"])
    p.wait()  # a pid that existed and is gone
    json.dump({"id": "j4", "command": ["x"], "started": "2026-11-01T00:00:00+09:00", "next": "", "log": "job.log"},
              open(os.path.join(d, "job.json"), "w"))
    open(os.path.join(d, "pid"), "w").write(str(p.pid))
    rc, out = sh(STATUS, d)
    assert out.startswith("DIED  j4"), out
    rc, out = sh(WAIT, d, "--poll", "1")
    assert rc == 3 and "JOB DIED" in out, (rc, out)
    rc, out = sh(RUN, d, "--", "true")
    assert rc == 2 and "an earlier job died" in out, out


def test_j5_old_job_with_empty_start_time():
    """Jobs written on macOS before RAL 089 have "started": "" (BSD date has no -Is); job_status must not crash."""
    d = os.path.join(SCRATCH, "j5")
    os.makedirs(d)
    json.dump({"id": "j5", "command": ["x"], "started": "", "next": "", "log": "job.log"}, open(os.path.join(d, "job.json"), "w"))
    open(os.path.join(d, "pid"), "w").write(str(os.getpid()))  # alive: this test process
    rc, out = sh(STATUS, d)
    assert rc == 0 and out.startswith("RUNNING  j5") and "elapsed ? s" in out, out


def test_j6_pid_alive_and_parent_pid_boundaries():
    assert qc.pid_alive(os.getpid()) and qc.pid_alive(str(os.getpid()))
    assert not qc.pid_alive(0) and not qc.pid_alive(-1)  # os.kill(0, 0) would hit our own group
    assert not qc.pid_alive("") and not qc.pid_alive("abc") and not qc.pid_alive(2 ** 40)
    assert qc.pid_alive(1)  # init/launchd: another user's process counts as alive (PermissionError)
    assert qc.parent_pid(os.getpid()) == os.getppid()
    assert qc.parent_pid(2 ** 22 + 12345) is None


def patched_run_job(name, old, new):
    """A copy of run_job.sh with one launch line changed, to make the start fail or lag (RAL 089 rev1 A1-4)."""
    s = open(RUN, encoding="utf-8").read()
    assert s.count(old) == 1, old
    m = os.path.join(SCRATCH, "mirror")  # a mirror of lib/ around the copy, so its relative paths (../gpu_lock.py) resolve
    if not os.path.isdir(m):
        os.makedirs(os.path.join(m, "lib", "jobs"))
        for f in ("gpu_lock.py", "qrispy_config.py", "launch.py"):
            os.symlink(os.path.join(LIB, f), os.path.join(m, "lib", f))
    p = os.path.join(m, "lib", "jobs", name + ".sh")
    open(p, "w", encoding="utf-8").write(s.replace(old, new))
    os.chmod(p, 0o755)
    return p


LAUNCH = '"${detach[@]}" nohup "$self" --inner'


def test_j7_a_job_that_cannot_start_is_reported():
    run = patched_run_job("run_fail", LAUNCH, '"${detach[@]}" nohup /nonexistent/run_job_inner --inner')
    d = os.path.join(SCRATCH, "j7")
    rc, out = sh(run, d, "--", "true")
    assert rc == 2 and "did not start" in out and "started j7" not in out, (rc, out)


def test_j9_a_gpu_job_that_cannot_start_does_not_leave_the_lock_running():
    """RAL 089 rev2 A2-3: --gpu takes the lock first; a start failure must set it back to held, as a normal end does."""
    run = patched_run_job("run_fail_gpu", LAUNCH, '"${detach[@]}" nohup /nonexistent/run_job_inner --inner')
    d = os.path.join(SCRATCH, "j9")
    rc, out = sh(run, d, "--gpu", "sim", "--", "true")
    assert rc == 2 and "did not start" in out, (rc, out)
    rc, out = sh("python3", "-I", os.path.join(LIB, "gpu_lock.py"), "status")
    assert out.startswith("gpu: held") and "did not start" in out, out
    shutil.rmtree(os.path.join(SCRATCH, "locks"), ignore_errors=True)


def test_j8_a_slow_start_is_not_called_a_failure():
    run = patched_run_job("run_slow", LAUNCH, '"${detach[@]}" bash -c \'sleep 3; exec "$@"\' _ nohup "$self" --inner')
    d = os.path.join(SCRATCH, "j8")
    rc, out = sh(run, d, "--", "true")
    assert rc == 0 and "may still be starting" in out, (rc, out)
    assert until(lambda: os.path.exists(os.path.join(d, "DONE.json")), 15)  # it did start, and ended
    assert json.load(open(os.path.join(d, "DONE.json")))["exit_code"] == 0


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    try:
        for t in tests:
            t()
    finally:
        shutil.rmtree(SCRATCH, ignore_errors=True)
    print(f"{len(tests)}/{len(tests)} PASS")
