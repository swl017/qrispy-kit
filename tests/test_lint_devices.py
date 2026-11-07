#!/usr/bin/env python3
"""RAL ticket 090 S8: three `qrispy lint <id>` devices promoted from sentence rules (RAL lessons L-070, L-071;
PAPER1 ticket 003 rev2 A2-4), each on a scratch repository:
- the line-break check skips HTML comment blocks (a review's QRISPY-REVIEW-PROTOCOL / -META header), but still
  catches a broken sentence right after a comment;
- a revN_response.md that state.json.reviews does not register as the response of revN.md is a WARN;
- a Q item that names another ticket's record file without a complete cross-ticket citation row is a FAIL while
  unanswered and a WARN once answered (RAL ticket 090 Q-14), and the message shows that ticket's CITE.md condition line.
Run from the kit: python3 -I tests/test_lint_devices.py"""
import json
import os
import shutil
import subprocess
import tempfile

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QRISPY = os.path.join(KIT, "plugin", "bin", "qrispy")
CITE_CHECK = "cross-ticket citations carry source row, condition line and definition"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def repo():
    r = os.path.realpath(tempfile.mkdtemp(prefix="qrispy_lint_dev_"))
    write(os.path.join(r, "qrispy.json"), json.dumps({"systems": [{"name": "DEMO", "root": "tickets"},
                                                                  {"name": "SIDE", "root": "side/tickets"}],
                                                      "review_scratch": r + "_scratch"}))
    write(os.path.join(r, "agents.json"), "[]")
    ticket(r, "tickets/001-a", stage="Y")
    ticket(r, "tickets/002-src", stage="closed")
    write(os.path.join(r, "tickets", "002-src", "z_closeout.md"), "# DEMO 002 closeout\n\n> 위험도 카드\n")
    write(os.path.join(r, "tickets", "002-src", "CITE.md"),
          "# DEMO 002 — 인용 경계\n\n- 출처 문서: `z_closeout.md`\n- 조건: 결과는 corpus A에 의존한다. observation layer 전용.\n- 판정: 2026-11-01\n")
    return r


def ticket(r, rel, stage="Y", **extra):
    st = {"ticket_slug": os.path.basename(rel), "current_stage": stage, "next_action": "x", "awaiting_user": [],
          "drift": [], "updated": "2026-11-07"}
    st.update(extra)
    write(os.path.join(r, rel, "state.json"), json.dumps(st))
    write(os.path.join(r, rel, "ticket.md"), f"# {rel} — t\n")
    for f in ("i_design.md", "p_plan.md"):  # a stage-Y ticket has them; without them lint exits 1 for another reason
        write(os.path.join(r, rel, f), "# x\n")
    if not os.path.exists(os.path.join(r, rel, "q_questions.md")):
        write(os.path.join(r, rel, "q_questions.md"), "# Q\n\n- 작성: 2026-11-01.\n")


def lint_run(r, tid="DEMO 001"):
    env = dict(os.environ, QRISPY_AGENTS_JSON=os.path.join(r, "agents.json"))
    env.pop("QRISPY_REPO", None)
    p = subprocess.run([QRISPY, "lint", tid], cwd=r, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout + p.stderr


def lint(r, tid="DEMO 001"):
    return lint_run(r, tid)[1]


def rows(out, name):
    return [l for l in out.splitlines() if name in l]


def row(out, name):
    got = rows(out, name)
    return got[0] if got else None


# --------------------------------------------------------------------------- HTML comment blocks (PAPER1 003 rev2 A2-4)

REVIEW_HEAD = ("<!-- QRISPY-REVIEW-PROTOCOL\nmethod/QRISPY_METHOD.md: d593\nmethod/DEV_REVIEW_RECIPE.md: a5c1\nAGENTS.md: 7ca3\n-->\n"
               "<!-- QRISPY-REVIEW-META\nverdict: BLOCKING\nblocking_open: 1\nw_gated: yes\n-->\n\n# DEMO 001: rev1\n\n")


def test_review_header_is_not_prose():
    r = repo()
    try:
        d = os.path.join(r, "tickets", "001-a")
        write(os.path.join(d, "rev1.md"), REVIEW_HEAD + "One finding, written as one line.\n")
        got = row(lint(r), "rev1.md: no sentence broken across lines")
        assert got and got.startswith("PASS"), got
        # a single-line comment and a comment closed mid-file do not hide a real broken sentence after them
        write(os.path.join(d, "rev2.md"), REVIEW_HEAD + "<!-- note -->\nThis sentence is broken\nacross two lines.\n")
        got = row(lint(r), "rev2.md: no sentence broken across lines")
        assert got and got.startswith("FAIL") and "[15]" in got, got
        # a broken line inside a comment that is not a review header is skipped too (comments are never prose)
        write(os.path.join(d, "rev2.md"), "# x\n\n<!--\nthis comment line is broken\nacross two lines\n-->\nDone.\n")
        assert row(lint(r), "rev2.md: no sentence broken across lines").startswith("PASS")
        # an HTML comment opener inside a code fence does not start a comment
        write(os.path.join(d, "rev2.md"), "# x\n\n```\n<!--\n```\nThis sentence is broken\nacross two lines.\n")
        got = row(lint(r), "rev2.md: no sentence broken across lines")
        assert got and got.startswith("FAIL"), got
    finally:
        shutil.rmtree(r)


# --------------------------------------------------------------------------- review response registration (L-071)

def test_unregistered_review_response_warns():
    r = repo()
    try:
        d = os.path.join(r, "tickets", "001-a")
        write(os.path.join(d, "rev1.md"), REVIEW_HEAD + "Finding.\n")
        write(os.path.join(d, "rev1_response.md"), "# response\n")
        name = "rev1_response.md: registered as the response in state.json.reviews"
        got = row(lint(r), name)
        assert got and got.startswith("WARN") and "no entry for rev1.md" in got, got
        entry = {"review": "rev1.md", "response": None, "verdict": "BLOCKING", "blocking_open": 1, "date": "2026-10-01"}
        ticket(r, "tickets/001-a", reviews=[entry])
        got = row(lint(r), name)
        assert got and got.startswith("WARN") and "response None" in got and 'set it to "rev1_response.md"' in got, got
        ticket(r, "tickets/001-a", reviews=[dict(entry, response="rev1_response.md")])
        assert row(lint(r), name).startswith("PASS")
        # a later round: rev2 registered without its response, rev1 fine (the PAPER1 003 rev4 A4-2 shape)
        write(os.path.join(d, "rev2.md"), REVIEW_HEAD + "Finding.\n")
        write(os.path.join(d, "rev2_response.md"), "# response\n")
        ticket(r, "tickets/001-a", reviews=[dict(entry, response="rev1_response.md"), dict(entry, review="rev2.md")])
        out = lint(r)
        assert row(out, "rev1_response.md: registered").startswith("PASS"), out
        assert row(out, "rev2_response.md: registered").startswith("WARN"), out
        # a closed ticket is history: not checked
        ticket(r, "tickets/001-a", stage="closed", reviews=[])
        write(os.path.join(d, "z_closeout.md"), "# closeout\n\n> 위험도 카드\n")
        assert not rows(lint(r), "registered as the response"), lint(r)
    finally:
        shutil.rmtree(r)


# --------------------------------------------------------------------------- cross-ticket citation field (L-070)

FIELD = "**다른 티켓 인용:**\n\n| 출처 (티켓, 파일, 행) | 조건 줄 (그 티켓 `CITE.md`) | 정의 (식, 추정량) |\n|---|---|---|\n"


def q_file(r, items, rel="tickets/001-a"):
    write(os.path.join(r, rel, "q_questions.md"), "# DEMO 001 — Q\n\n- 작성: 2026-11-01.\n\n" + "\n".join(items))


def item(n, body, answer="", date="2026-11-09"):
    return f"### Q-{n} (added during I, {date}) question {n}\n\n{body}\n\n**권고:** a.\n\n> 사용자 답:{answer}\n"


# the PAPER1 003 Q-38 shape: a number from another ticket's record, put to the user without its condition line
Q38 = ("이름표는 peer ray 오차가 2.31–2.65°라는 전제에 기댄다. 그 값은 DEMO 002가 다른 corpus에서 잰 것이다 "
       "(DEMO 002 `z_closeout.md` 57–58행).")


def cite_rows(out):
    return [l for l in out.splitlines() if CITE_CHECK in l]


def test_citation_without_field_warns_with_condition_line():
    r = repo()
    try:
        q_file(r, [item(1, Q38)])
        got = cite_rows(lint(r))
        assert len(got) == 1 and got[0].startswith("FAIL") and "Q-1" in got[0], got
        assert "DEMO 002 `z_closeout.md`: no cross-ticket citation field" in got[0], got
        assert "결과는 corpus A에 의존한다" in got[0], got  # the condition line to copy is in the warning
        # the same with a complete row: PASS
        full = FIELD + "| DEMO 002 `z_closeout.md` 57–58행 | \"결과는 corpus A에 의존한다\" | 중앙값(수직 거리 ÷ 거리) ÷ 1.1774, 기록 ray의 EKF 원점 |\n"
        q_file(r, [item(1, Q38 + "\n\n" + full)])
        got = cite_rows(lint(r))
        assert len(got) == 1 and got[0].startswith("PASS"), got
    finally:
        shutil.rmtree(r)


def test_incomplete_rows_warn():
    r = repo()
    try:
        cases = {  # field body → expected reason
            "| <SYSTEM NNN `CITE.md` 행 N> | <\"…\"> | <식, 추정량> |\n": "no row for this ticket in the field",
            "| DEMO 002 `z_closeout.md` | \"corpus A\" | — |\n": "row lacks",
            "| DEMO 002 `z_closeout.md` | \"corpus A\" |\n": "row lacks",
            "| SIDE 004 `CITE.md` 행 1 | \"x\" | y |\n": "no row for this ticket in the field",
        }
        for table, why in cases.items():
            q_file(r, [item(1, Q38 + "\n\n" + FIELD + table)])
            got = cite_rows(lint(r))
            assert len(got) == 1 and got[0].startswith("FAIL") and why in got[0], (table, got)
    finally:
        shutil.rmtree(r)


def test_not_a_citation_row_clears_an_item_that_only_changes_the_file():
    r = repo()
    try:
        body = "DEMO 002 `CITE.md` 인용 가능 행 3에 \"점검 중\" 표시를 달까?"
        q_file(r, [item(1, body)])
        assert cite_rows(lint(r))[0].startswith("FAIL")
        q_file(r, [item(1, body + "\n\n" + FIELD + "| DEMO 002 `CITE.md` | 인용 아님: 그 파일에 표시를 다는 일만 묻는다 | — |\n")])
        got = cite_rows(lint(r))
        assert len(got) == 1 and got[0].startswith("PASS"), got
    finally:
        shutil.rmtree(r)


def test_detection_scope_and_limits():
    r = repo()
    try:
        q_file(r, [
            item(1, "DEMO 002 `ticket.md`의 범위와 DEMO 002 `state.json`을 본다."),     # working files: not a citation
            item(2, "이 티켓의 DEMO 001 `CITE.md` 행 1을 고친다."),                     # the ticket itself
            item(3, "DEMO 002의 deliverable 94–96행에 따르면 3.5°는 운용값이다."),       # limit: no file named, unseen
            item(4, "DEMO-026 `CITE.md`와 bare 002 `CITE.md`."),                       # limit: short forms, unseen
        ])
        assert not cite_rows(lint(r)), lint(r)
        # a Korean particle between the ticket and the file, and the long form "<SYSTEM> ticket NNN", are seen
        q_file(r, [item(1, "DEMO 002의 `z_closeout.md` 3행."), item(2, "DEMO ticket 002 `results/a.csv`.")])
        got = cite_rows(lint(r))
        assert len(got) == 2 and all(g.startswith("FAIL") for g in got), got
        # another system's ticket that is not in this repository's folders: still a citation, no condition hint
        q_file(r, [item(1, "SIDE 007 `CITE.md` 행 2.")])
        got = cite_rows(lint(r))
        assert len(got) == 1 and got[0].startswith("FAIL") and "SIDE 007" in got[0], got
    finally:
        shutil.rmtree(r)


def test_which_items_are_checked():
    r = repo()
    try:
        q_file(r, [
            item(1, Q38, answer=" \"Q-1 권고\"", date="2026-11-07"),   # answered before the check started: history
            item(2, Q38, answer=" \"Q-2 권고\"", date="2026-11-09"),   # answered after: checked
            item(3, Q38, date="2026-10-01"),                          # unanswered: always checked, whatever its date
        ])
        code, out = lint_run(r)
        got = cite_rows(out)
        assert len(got) == 2 and "Q-2" in got[0] and "Q-3" in got[1], got
        assert got[0].startswith("WARN") and "answered;" in got[0], got   # answered: a warning
        assert got[1].startswith("FAIL") and "unanswered" in got[1], got  # unanswered: the user must not read it yet
        assert code == 1, out                                             # a FAIL makes lint exit 1
        q_file(r, [item(2, Q38, answer=" \"Q-2 권고\"", date="2026-11-09")])
        code, out = lint_run(r)
        assert cite_rows(out)[0].startswith("WARN") and code == 0, out    # a warning alone does not
        # an item with no date in its heading takes the file's 작성 date; unanswered, so checked
        q_file(r, ["### Q-1 question\n\n" + Q38 + "\n\n> 사용자 답:\n"])
        got = cite_rows(lint(r))
        assert len(got) == 1 and got[0].startswith("FAIL"), got
        # the body of an item ends at the next Q heading: a citation in Q-2 is not Q-1's
        q_file(r, [item(1, "no citation here"), item(2, Q38)])
        got = cite_rows(lint(r))
        assert len(got) == 1 and "Q-2" in got[0], got
        # a closed ticket is not checked
        ticket(r, "tickets/001-a", stage="closed")
        write(os.path.join(r, "tickets", "001-a", "z_closeout.md"), "# closeout\n\n> 위험도 카드\n")
        assert not cite_rows(lint(r)), lint(r)
    finally:
        shutil.rmtree(r)


def test_template_carries_the_field():
    with open(os.path.join(KIT, "plugin", "skills", "ticket", "templates", "q_questions.md"), encoding="utf-8") as f:
        t = f.read()
    assert "**다른 티켓 인용:**" in t and "| 출처 (티켓, 파일, 행) | 조건 줄" in t and "정의 (식, 추정량)" in t, t
    assert t.index("**다른 티켓 인용:**") < t.index("**권고:**")  # written before the user reads the recommendation


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)}/{len(tests)} PASS")
