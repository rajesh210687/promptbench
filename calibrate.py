"""Compare the LLM judge with your own grades on 12 fixed cases."""
import json
import os
import random

from config import DATASET_PATH, PROMPT_PATH
from judge import RUBRIC, judge_summary
from run_prompt import run_case

CAL_PATH = "data/calibration.jsonl"
HARD = {"ambiguous", "multi_issue", "vague", "edge_case"}


def pick(cases, seed=42):
    rng = random.Random(seed)
    hard = [c for c in cases if HARD & set(c["tags"])]
    rest = [c for c in cases if c not in hard]
    return sorted(rng.sample(hard, 4) + rng.sample(rest, 8), key=lambda c: c["id"])


def grade(cases):
    prompt, rows = open(PROMPT_PATH).read(), []
    print("Rubric:\n" + RUBRIC)
    for c in cases:
        out = run_case(c["ticket"], prompt)
        print(f"\n--- {c['id']} ---\nTicket: {c['ticket']}\nKey facts: {c['key_facts']}")
        print(f"Summary: {out.get('summary', out)}")
        while True:
            ans = input("Your score (1-5): ").strip()
            if ans in list("12345"):
                break
        rows.append({"id": c["id"], "output": out, "human_score": int(ans)})
    with open(CAL_PATH, "w") as f:
        f.writelines(json.dumps(r) + "\n" for r in rows)
    return rows


def main():
    cases = {c["id"]: c for c in map(json.loads, open(DATASET_PATH))}
    if os.path.exists(CAL_PATH):
        rows = [json.loads(l) for l in open(CAL_PATH)]
    else:
        rows = grade(pick(list(cases.values())))
    print(f"\n{'id':6}{'you':>5}{'judge':>7}{'diff':>6}")
    diffs, big = [], []
    for r in rows:
        j = judge_summary(r["output"], cases[r["id"]])
        d = (j["score"] or 0) - r["human_score"]
        diffs.append(abs(d))
        print(f"{r['id']:6}{r['human_score']:>5}{str(j['score']):>7}{d:>+6}")
        if abs(d) >= 2:
            big.append((r["id"], j["reasoning"]))
    for cid, why in big:
        print(f"\n{cid} judge reasoning: {why}")
    n = len(diffs)
    print(f"\nExact agreement: {sum(d == 0 for d in diffs)}/{n} = {sum(d == 0 for d in diffs) / n:.0%}")
    print(f"Within-1 agreement: {sum(d <= 1 for d in diffs)}/{n} = {sum(d <= 1 for d in diffs) / n:.0%}")


if __name__ == "__main__":
    main()
