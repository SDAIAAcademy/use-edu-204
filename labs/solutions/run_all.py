# /// script
# requires-python = ">=3.11"
# ///
"""Runs every lab solution of USE-EDU-204 with the scripted stand-in tutor and checks the
reference numbers. Prints PASS, or the first difference. Run from the repository root:

    uv run labs/solutions/run_all.py
"""
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = HERE.parent / "files"
sys.path.insert(0, str(HERE))
for s in (sys.stdout, sys.stderr):
    try:
        s.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

import stand_in_tabsira as S  # noqa: E402
import tabsira_tools as T  # noqa: E402


def check(cond, msg):
    if not cond:
        print("FAIL:", msg)
        sys.exit(1)


def rows(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def replay(instr, log):
    """The stand-in, run again on the instruction file, gives the replies in the log."""
    text = instr.read_text(encoding="utf-8")
    script = S.load()
    for r in rows(log):
        _, reply = S.answer(text, r["id"], script)
        check(reply == r["response"], f"{log.name} {r['id']}: the stand-in on {instr.name} gives another reply")


def main():
    v1, v2 = FILES / "tabsira_instructions_v1.txt", FILES / "tabsira_instructions_v2.txt"
    ref, v3, v4 = HERE / "tabsira_instructions_reference.txt", HERE / "tabsira_instructions_v3.txt", HERE / "tabsira_instructions_v4.txt"

    print("lab 1.1: the reference instruction file on the 30 questions")
    replay(ref, HERE / "test_log_reference_file.csv")
    r = T.rates(HERE / "test_log_reference_file.csv", quiet=True)
    check((r["correct_hint"], r["leaked"], r["error"]) == (30, 0, 0), f"reference file: {r}")
    tags = S.tags_of(ref.read_text(encoding="utf-8"))
    check({"B3", "B4", "L5", "A2", "S1"} <= tags, "the reference file lacks a hint-ladder rule")

    print("lab 1.2: the recorded run of the first draft, the calibration rows and one fix")
    replay(v1, HERE / "test_log_v1_reference.csv")
    r = T.rates(HERE / "test_log_v1_reference.csv", quiet=True)
    check((r["n"], r["correct_hint"], r["leaked"], r["error"]) == (30, 22, 4, 2), f"v1 rates: {r}")
    check(r["disagree"] == ["T26"], f"leak finder: {r['disagree']}")
    rec = {x["id"]: x["response"] for x in rows(FILES / "recorded_run_v1.csv")}
    check(all(rec[x["id"]] == x["response"] for x in rows(HERE / "test_log_v1_reference.csv")), "recorded run differs from the key")
    check(len(rows(HERE / "calibration_key.csv")) == 6, "six calibration rows")
    replay(v2, HERE / "retest_v2_reference.csv")
    fixed, still, broke = T.compare(HERE / "test_log_v1_reference.csv", HERE / "retest_v2_reference.csv")
    check(len(fixed) == 7 and still == ["T05"] and not broke, "retest after the fix")

    print("lab 2.1: six scenarios before and after the guardrails, and the regression")
    for v, f, want in ((v2, "scenario_log_v2_reference.csv", 0), (v3, "scenario_log_v3_reference.csv", 5), (v4, "scenario_log_v4_reference.csv", 6)):
        replay(v, HERE / f)
        passed, failed = T.scenarios(HERE / f)
        check(len(passed) == want, f"{f}: {len(passed)} passed")
    replay(v3, HERE / "retest_x_v3_reference.csv")
    replay(v4, HERE / "retest_x_v4_reference.csv")
    r3 = T.rates(HERE / "retest_x_v3_reference.csv", quiet=True)
    r4 = T.rates(HERE / "retest_x_v4_reference.csv", quiet=True)
    check((r3["correct_hint"], r4["correct_hint"]) == (11, 12), f"extraction retest: {r3['correct_hint']}, {r4['correct_hint']}")
    t19 = [x for x in rows(HERE / "retest_x_v3_reference.csv") if x["id"] == "T19"][0]
    check("مقيَّم" in t19["response"], "the v3 over-block on T19")
    g = (HERE / "guardrails_reference.txt").read_text(encoding="utf-8")
    v4_lines = [x for x in v4.read_text(encoding="utf-8").splitlines() if x.startswith("[G")]
    check(len(v4_lines) == 7 and all(x in g for x in v4_lines), "the guardrails reference differs from v4")

    print("lab 2.2: last term's trial")
    e = T.evaluate(FILES / "trial_unit3_results.csv")
    res, bands = e["res"], e["bands"]
    check(res["practice_score"]["diff"] > 2 and res["posttest_ai_off"]["diff"] < -1, "practice up, post-test down")
    check(res["posttest_ai_off"]["ci"][1] < 0, "the post-test interval stays below zero")
    lower = bands["أدنى"]["ai"] - bands["أدنى"]["none"]
    check(lower == min(b["ai"] - b["none"] for b in bands.values()), "the lower band loses most")
    check(e["gap"][e["ai"]] > e["gap"]["دون مساعد"], "the gap widens with the open assistant")
    # The exact figures on the debrief slide, the lab page and the answer key
    r2 = lambda x: round(x, 2)
    pr, po = res["practice_score"], res["posttest_ai_off"]
    check((pr["n_ai"], pr["n_none"]) == (58, 61), "group sizes")
    check(tuple(map(r2, (pr["ai"], pr["none"], pr["diff"], *pr["ci"]))) == (15.03, 11.89, 3.15, 2.23, 4.10), f"practice: {pr}")
    check(tuple(map(r2, (po["ai"], po["none"], po["diff"], *po["ci"]))) == (9.97, 11.39, -1.43, -2.65, -0.19), f"post-test: {po}")
    want = {"أدنى": (6.07, 8.18, 15, 17), "وسطى": (10.58, 11.11, 33, 28), "عليا": (13.80, 15.31, 10, 16)}
    for band, w in want.items():
        b = bands[band]
        check((r2(b["ai"]), r2(b["none"]), b["n_ai"], b["n_none"]) == w, f"band {band}: {b}")
    check((r2(e["gap"][e["ai"]]), r2(e["gap"]["دون مساعد"])) == (7.73, 7.14), f"gap: {e['gap']}")

    print("PASS")


if __name__ == "__main__":
    main()
