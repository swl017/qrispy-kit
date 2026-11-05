#!/usr/bin/env python3
"""Check that a review response answers every finding of its review, one by one, with evidence.

Device for LESSONS RAL lesson L-019 (five recurrences, the fifth PAPER1 ticket 004 rev3 B3-1: a response said
"fixed" while the same wording survived in two other places). User ruling 2026-10-18: every finding
gets its own answer, and the same device covers document reviews and code reviews.

    python3 -I check_response.py <revN.md> <revN_response.md>

The review names findings with headings or bold lead-ins such as `### B3-1.`, `**A2-4.**`, `### R3-B1`
or `### B-2`. The response must carry, for every such ID, a heading that names it and under it these
fields (Korean or English label, as a list item or bold lead-in):

    - 지적 / Finding:            the reviewer's claim, quoted
    - 판정 / Verdict:            수용 / 일부 수용 / 거부 (accept / partial / reject), the reason, the mistake class
    - 출현 위치 / Locations:     every place the problem occurs, found by a search that is named in
                                 backticks ("찾은 방법: `grep -n …`" / "found by: `rg …`"), not only the cited line
    - 위치별 변경 / Changes:     per location, before → after ("없음" only when the verdict is a rejection)
    - 확인 / Verification:       the re-check run on disk after the change, with the command or path in backticks
    - 회귀 시험 / Regression test: required when a location is a code file and the finding was accepted:
                                 the test that failed before and passes after, in backticks, or "없음/none"
                                 with the reason

Exit code 0 when every finding passes, 1 otherwise. No third-party imports.
"""
import re
import sys

ID_RE = r"(?:R\d+-[BA]\d+|[BA]\d*-\d+[a-z]?)"
REVIEW_ID = re.compile(rf"^(?:#{{2,4}}\s+|\*\*)({ID_RE})\b", re.M)
HEADING = re.compile(r"^(#{2,4})\s+(.*)$", re.M)
FIELDS = {
    "finding": ("지적", "Finding"),
    "verdict": ("판정", "Verdict"),
    "locations": ("출현 위치", "Locations"),
    "changes": ("위치별 변경", "Changes"),
    "verify": ("확인", "Verification"),
    "regression": ("회귀 시험", "Regression test"),
}
LABEL_LINE = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?(" + "|".join(re.escape(l) for ls in FIELDS.values() for l in ls) + r")(?:\*\*)?\s*(?:\(|:|：)", re.M)
CODE_PATH = re.compile(r"[\w./-]+\.(?:py|cpp|cc|cxx|c|h|hpp|sh|bash|js|ts|tsx|rs|go|java|m|launch\.py)\b")
REJECT = re.compile(r"거부|기각|reject", re.I)
NONE_WORD = re.compile(r"^\s*(?:없음|none|n/a)\b", re.I)
BACKTICK = re.compile(r"`[^`\n]+`")
FOUND_BY = re.compile(r"찾은 방법|found by|search", re.I)


def review_ids(text):
    seen = []
    for m in REVIEW_ID.finditer(text):
        if m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def sections(text):
    """Map finding ID -> body of the first heading section that names it."""
    heads = list(HEADING.finditer(text))
    out = {}
    for i, h in enumerate(heads):
        level = len(h.group(1))
        end = len(text)
        for nxt in heads[i + 1:]:
            if len(nxt.group(1)) <= level:
                end = nxt.start()
                break
        for fid in re.findall(rf"(?<![\w-]){ID_RE}(?![\w-])", h.group(2)):
            out.setdefault(fid, text[h.end():end])
    return out


def fields(body):
    """Map field key -> text of that field (label line plus the lines up to the next label)."""
    marks = list(LABEL_LINE.finditer(body))
    out = {}
    for i, m in enumerate(marks):
        key = next(k for k, ls in FIELDS.items() if m.group(1) in ls)
        end = marks[i + 1].start() if i + 1 < len(marks) else len(body)
        val = body[m.end():end].strip()
        out.setdefault(key, val)
    return out


def check(review_text, response_text):
    """Return [(ok, check, detail)]; ok is True or False."""
    ids = review_ids(review_text)
    res = [(bool(ids), "review names its findings with IDs (### B3-1, **A2-4.**, ### R3-B1)", "" if ids else "no finding IDs found")]
    secs = sections(response_text)
    for fid in ids:
        body = secs.get(fid)
        if body is None:
            res.append((False, f"{fid}: the response has a section for it", "no heading names this ID"))
            continue
        f = fields(body)
        missing = [FIELDS[k][0] for k in ("finding", "verdict", "locations", "changes", "verify") if not f.get(k)]
        res.append((not missing, f"{fid}: all fields present", "missing: " + ", ".join(missing) if missing else ""))
        if missing:
            continue
        rejected = bool(REJECT.search(f["verdict"]))
        loc_ok = bool(FOUND_BY.search(f["locations"])) and bool(BACKTICK.search(f["locations"]))
        res.append((loc_ok, f"{fid}: locations name the search that found them", "" if loc_ok else "say how the locations were found, with the command in backticks"))
        chg_ok = rejected or not NONE_WORD.match(f["changes"])
        res.append((chg_ok, f"{fid}: changes recorded per location", "" if chg_ok else "'없음' is allowed only with a rejected finding"))
        ver_ok = bool(BACKTICK.search(f["verify"]))
        res.append((ver_ok, f"{fid}: verification cites a command or path", "" if ver_ok else "put the re-check command or path in backticks"))
        if CODE_PATH.search(f["locations"]) and not rejected:
            reg = f.get("regression", "")
            reg_ok = bool(BACKTICK.search(reg)) or (bool(NONE_WORD.match(reg)) and len(reg) > 12)
            res.append((reg_ok, f"{fid}: code finding names its regression test", "" if reg_ok else "name the test (backticks) or write '없음' with the reason"))
    extra = sorted(set(secs) - set(ids))
    if extra:
        res.append((True, "response sections for IDs not in the review (allowed)", ", ".join(extra)))
    return res


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__.split("\n\n")[2])
    with open(argv[1], encoding="utf-8") as f:
        review = f.read()
    with open(argv[2], encoding="utf-8") as f:
        response = f.read()
    res = check(review, response)
    bad = sum(1 for ok, _, _ in res if not ok)
    print(f"{len(res) - bad}/{len(res)} PASS")
    for ok, name, detail in res:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
