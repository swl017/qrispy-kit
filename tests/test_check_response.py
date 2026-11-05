#!/usr/bin/env python3
"""Unit tests for check_response.py (PAPER1 ticket 004 rev3, RAL lesson L-019 device). Run: python3 -I test_check_response.py"""
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plugin", "lib"))  # RAL ticket 090: the tool lives in the kit
import check_response as cr  # noqa: E402

REVIEW = """
## 3. 지적 사항

**B3-1. P-28 문구가 두 곳에 남아 있습니다.** 분류: `record-mismatch`.

**A3-1. GTSAM 비교가 빠졌습니다.** 분류: `record-mismatch`.

### R4-B1 hook misses `git checkout-index`

| rev2 지적 | 판정 |
|---|---|
| A2-4 | 미해소 |
"""

DOC_OK = """
### B3-1 — P-28 문구
- 지적: "P-28 행과 §3.1에 넓힌 읽기가 남아 있다"
- 판정: 수용. 분류 `record-mismatch`
- 출현 위치 (찾은 방법: `grep -n "묶\\|예측" PRIOR_ART.md`):
  - P-28 행, §3.1, F-5 뜻 칸
- 위치별 변경:
  - P-28 행: "예측되어 있다" → "이론으로 이미 있다"
- 확인: `grep -n "예측" PRIOR_ART.md` 결과 P-28에 돌린 문장 0건

### A3-1
- 지적: "GTSAM 비교가 빠졌다"
- 판정: 거부. 이유: 이미 §1.2에 있음
- 출현 위치 (찾은 방법: `grep -n GTSAM PRIOR_ART.md`): §1.2 P-34 행
- 위치별 변경: 없음
- 확인: `PRIOR_ART.md` §1.2 P-34 행을 다시 엶

### R4-B1
- Finding: "the hook misses git checkout-index"
- Verdict: accept, `rule-violation`
- Locations (found by: `rg -n checkout tools/agent_hooks`): `tools/agent_hooks/guard_git.py:88`
- Changes: guard_git.py:88 regex widened → covers checkout-index
- Verification: `python3 -I tools/agent_hooks/test_guard_git.py` 196/196
- Regression test: `test_guard_git.py` case C43, FAIL before, PASS after
"""


def run(review, response):
    return {name: ok for ok, name, _ in cr.check(review, response)}


def test_ids():
    assert cr.review_ids(REVIEW) == ["B3-1", "A3-1", "R4-B1"], cr.review_ids(REVIEW)  # table row A2-4 is not a finding of this round


def test_all_pass():
    r = run(REVIEW, DOC_OK)
    assert all(r.values()), [k for k, v in r.items() if not v]


def test_missing_section():
    r = run(REVIEW, DOC_OK.split("### A3-1")[0])
    assert r["A3-1: the response has a section for it"] is False


def test_one_line_answer_fails():
    resp = DOC_OK.replace(DOC_OK.split("### A3-1")[0], "### B3-1\n수용, 고침. F-5를 좁혔다.\n\n")
    assert run(REVIEW, resp)["B3-1: all fields present"] is False


def test_locations_need_search():
    resp = DOC_OK.replace('(찾은 방법: `grep -n "묶\\|예측" PRIOR_ART.md`)', "")
    assert run(REVIEW, resp)["B3-1: locations name the search that found them"] is False


def test_none_changes_only_when_rejected():
    resp = DOC_OK.replace("거부. 이유: 이미 §1.2에 있음", "수용")
    assert run(REVIEW, resp)["A3-1: changes recorded per location"] is False


def test_verification_needs_command():
    resp = DOC_OK.replace("- 확인: `grep -n \"예측\" PRIOR_ART.md` 결과 P-28에 돌린 문장 0건", "- 확인: 다시 봤음")
    assert run(REVIEW, resp)["B3-1: verification cites a command or path"] is False


def test_code_finding_needs_regression_test():
    resp = DOC_OK.replace("- Regression test: `test_guard_git.py` case C43, FAIL before, PASS after\n", "")
    assert run(REVIEW, resp)["R4-B1: code finding names its regression test"] is False
    resp2 = DOC_OK.replace("- Regression test: `test_guard_git.py` case C43, FAIL before, PASS after", "- Regression test: none, the change is a comment typo only")
    assert run(REVIEW, resp2)["R4-B1: code finding names its regression test"] is True


def test_review_without_ids():
    assert run("## 지적\n- 문장이 길다\n", DOC_OK)["review names its findings with IDs (### B3-1, **A2-4.**, ### R3-B1)"] is False


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{len(tests)}/{len(tests)} PASS")
