# /// script
# requires-python = ">=3.11"
# ///
"""A scripted stand-in for the course tutor «تبصرة». It is not a language model.

It reads an instruction file, finds the rule tags in it (lines that start with a tag such as
[L5]), and answers a test question or a misuse scenario with the reply written for the course:
the good reply when the file holds the tags that fix the planted fault, otherwise the faulty
reply. That makes every lab of the course runnable without a model and without a key, and it
makes the reference instruction files checkable: run them and read the log.

    uv run labs/solutions/stand_in_tabsira.py labs/files/tabsira_instructions_v1.txt T15
    uv run labs/solutions/stand_in_tabsira.py labs/solutions/tabsira_instructions_v4.txt M5
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "tabsira_script.json"
TAG = re.compile(r"^\s*\[([A-Z][A-Z0-9]*)\]", re.M)


def tags_of(text):
    return set(TAG.findall(text))


def load():
    return json.loads(SCRIPT.read_text(encoding="utf-8"))


def reply(item, tags):
    """(kind, text): kind is 'good' or the planted fault's kind."""
    for fault in item["faults"]:
        needs = fault.get("only_with", [])
        if needs and not set(needs) <= tags:
            continue
        if not set(fault["fixed_by"]) <= tags:
            return fault["kind"], fault["text"]
    return "good", item["good"]


def answer(instruction_text, item_id, script=None):
    script = script or load()
    items = {i["id"]: i for i in script["tests"] + script["scenarios"]}
    return reply(items[item_id], tags_of(instruction_text))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: stand_in_tabsira.py <instruction file> <T01..T30 | M1..M6>")
    kind, text = answer(Path(sys.argv[1]).read_text(encoding="utf-8"), sys.argv[2])
    print(text)
