# /// script
# requires-python = ">=3.11"
# ///
"""Small, readable checks for the labs of USE-EDU-204. Standard library only. None of them
replaces reading the participant's work.

    uv run labs/solutions/tabsira_tools.py rates <test log .csv>
    uv run labs/solutions/tabsira_tools.py compare <log before .csv> <log after .csv>
    uv run labs/solutions/tabsira_tools.py scenarios <scenario log .csv>
    uv run labs/solutions/tabsira_tools.py evaluate <trial results .csv>

rates: the three rates of a labelled log (correct hint, leaked answer, error), with a second
opinion from an automatic leak finder that looks for the final answer of each problem in the
reply. The finder is a cross-check: a reply that confirms the learner's own answer is flagged
too, and a solution written out in words can slip past it.
"""
import csv
import random
import statistics as st
import sys
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
from pathlib import Path

HERE = Path(__file__).resolve().parent
YES = {"نعم", "yes", "y", "1", "true"}

# The strings that reveal each final answer (kept in step with labs/_tools/content_unit.py)
TOKENS = {
    "P1": ["1/3", "2/6", "0.333", "33.3%"], "P2": ["7/10", "70%"], "P3": ["0.63", "63%"],
    "P4": ["0.07", "7%"], "P5": ["3/95", "12/380", "0.0316", "3.16%"], "P6": ["91/216", "0.421", "42.1%"],
    "P7": ["84/120", "= 0.7", "70%"], "P8": ["0.269", "26.9%", "18/67"], "P9": ["-0.4", "−0.4", "خسارة 0.4"],
    "P10": ["0.3087", "30.9%"],
}


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def yes(v):
    return str(v or "").strip().lower() in YES


def rates(path, quiet=False):
    rows = read(path)
    n = len(rows)
    out = {k: sum(yes(r[k]) for r in rows) for k in ("correct_hint", "leaked", "error")}
    flagged = [r["id"] for r in rows if any(t in (r.get("response") or "") for t in TOKENS.get(r.get("problem", ""), []))]
    unlabelled = [r["id"] for r in rows if not any((r.get(k) or "").strip() for k in ("correct_hint", "leaked", "error"))]
    disagree = [i for i in flagged if not yes(next(r for r in rows if r["id"] == i)["leaked"])]
    if not quiet:
        print(f"rows: {n}")
        for k, label in (("correct_hint", "correct hint"), ("leaked", "leaked answer"), ("error", "error")):
            print(f"{label:>14}: {out[k]:2d} of {n}  ({100 * out[k] / n:.1f}%)" if n else f"{label}: no rows")
        print("leak finder flags:", ", ".join(flagged) or "none")
        if disagree:
            print("flagged but labelled not leaked (read these again):", ", ".join(disagree))
        if unlabelled:
            print("rows without labels:", ", ".join(unlabelled))
    return {"n": n, **out, "flagged": flagged, "disagree": disagree}


def compare(before, after):
    a = {r["id"]: r for r in read(before)}
    b = {r["id"]: r for r in read(after)}
    fixed, still, broke = [], [], []
    for i, rb in b.items():
        ra = a.get(i)
        ok_b = yes(rb["correct_hint"]) and not yes(rb["leaked"]) and not yes(rb["error"])
        ok_a = ra is not None and yes(ra["correct_hint"]) and not yes(ra["leaked"]) and not yes(ra["error"])
        (still if not ok_b and not ok_a else fixed if ok_b and not ok_a else broke if ok_a and not ok_b else []).append(i)
    print("fixed by the change:", ", ".join(fixed) or "none")
    print("still failing:", ", ".join(still) or "none")
    print("broken by the change (regressions):", ", ".join(broke) or "none")
    return fixed, still, broke


def scenarios(path):
    rows = read(path)
    passed = [r["id"] for r in rows if r["verdict"].strip() in ("ناجح", "pass")]
    failed = [r["id"] for r in rows if r["verdict"].strip() in ("فاشل", "fail")]
    print(f"scenarios passed: {len(passed)} of {len(rows)}", "·", ", ".join(passed) or "none")
    print("failed:", ", ".join(failed) or "none")
    return passed, failed


def boot_diff(x, y, rng, reps=2000):
    diffs = []
    for _ in range(reps):
        bx = [rng.choice(x) for _ in x]
        by = [rng.choice(y) for _ in y]
        diffs.append(st.mean(bx) - st.mean(by))
    diffs.sort()
    return diffs[int(0.025 * reps)], diffs[int(0.975 * reps) - 1]


def evaluate(path, quiet=False):
    rows = read(path)
    rng = random.Random(204)
    arms = sorted({r["arm"] for r in rows})
    ai = [a for a in arms if a != "دون مساعد"][0]
    res = {}
    for measure in ("practice_score", "posttest_ai_off"):
        g = {a: [int(r[measure]) for r in rows if r["arm"] == a] for a in arms}
        d = st.mean(g[ai]) - st.mean(g["دون مساعد"])
        lo, hi = boot_diff(g[ai], g["دون مساعد"], rng)
        res[measure] = {"ai": st.mean(g[ai]), "none": st.mean(g["دون مساعد"]), "diff": d, "ci": (lo, hi),
                        "n_ai": len(g[ai]), "n_none": len(g["دون مساعد"])}
    bands = {}
    for band in ("أدنى", "وسطى", "عليا"):
        g = {a: [int(r["posttest_ai_off"]) for r in rows if r["arm"] == a and r["prior_band"] == band] for a in arms}
        bands[band] = {"ai": st.mean(g[ai]), "none": st.mean(g["دون مساعد"]), "n_ai": len(g[ai]), "n_none": len(g["دون مساعد"])}
    gap = {a: (bands["عليا"]["ai" if a == ai else "none"] - bands["أدنى"]["ai" if a == ai else "none"]) for a in arms}
    if not quiet:
        print(f"students: {len(rows)}; with the open assistant: {res['practice_score']['n_ai']}; without: {res['practice_score']['n_none']}")
        for m, label in (("practice_score", "practice score"), ("posttest_ai_off", "AI-off post-test")):
            x = res[m]
            print(f"{label:>17}: with {x['ai']:.2f}, without {x['none']:.2f}, difference {x['diff']:+.2f} "
                  f"(bootstrap 95% interval {x['ci'][0]:+.2f} to {x['ci'][1]:+.2f}), out of 20")
        print("AI-off post-test by prior band (with / without, n):")
        for band, x in bands.items():
            print(f"  {band}: {x['ai']:.2f} / {x['none']:.2f}  (n {x['n_ai']} / {x['n_none']})  difference {x['ai'] - x['none']:+.2f}")
        print(f"gap upper minus lower band: with the assistant {gap[ai]:.2f}, without {gap['دون مساعد']:.2f}")
        print("caution: sections were chosen by the teacher, not at random, and no consent was recorded.")
    return {"res": res, "bands": bands, "gap": gap, "ai": ai}


if __name__ == "__main__":
    cmd, args = (sys.argv[1], sys.argv[2:]) if len(sys.argv) > 1 else ("", [])
    if cmd == "rates" and len(args) == 1:
        rates(args[0])
    elif cmd == "compare" and len(args) == 2:
        compare(*args)
    elif cmd == "scenarios" and len(args) == 1:
        scenarios(args[0])
    elif cmd == "evaluate" and len(args) == 1:
        evaluate(args[0])
    else:
        sys.exit(__doc__)
