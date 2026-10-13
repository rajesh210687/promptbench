"""Run the prompt over the golden set, score every case, write results/<timestamp>.json."""
import argparse
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from config import DATASET_PATH, JUDGE_MODEL, PROMPT_PATH, RESULTS_DIR, TARGET_MODEL
from judge import score_case
from run_prompt import run_case


def sha8(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:8]


def git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def summarize(rows):
    n = len(rows)
    scores = [r["judge_score"] for r in rows if r["judge_score"] is not None]
    return {"pass_rate": sum(r["passed"] for r in rows) / n,
            "mean_judge_score": sum(scores) / len(scores) if scores else None,
            "category_accuracy": sum(r["category_ok"] for r in rows) / n,
            "urgency_accuracy": sum(r["urgency_ok"] for r in rows) / n,
            "invalid_json_count": sum(r["output"].get("error") == "invalid_json" for r in rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="")
    args = ap.parse_args()
    prompt = open(PROMPT_PATH).read()
    cases = [c for c in map(json.loads, open(DATASET_PATH)) if not c.get("delete")]
    done = 0

    def work(case):
        nonlocal done
        out = run_case(case["ticket"], prompt)
        row = {"id": case["id"], "tags": case["tags"], "output": out, **score_case(out, case)}
        done += 1
        print(f"\r{done}/{len(cases)}", end="", file=sys.stderr, flush=True)
        return row

    with ThreadPoolExecutor(max_workers=5) as pool:
        rows = list(pool.map(work, cases))
    print(file=sys.stderr)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    result = {"meta": {"timestamp": ts, "label": args.label, "target_model": TARGET_MODEL,
                       "judge_model": JUDGE_MODEL, "prompt_sha": sha8(PROMPT_PATH),
                       "dataset_sha": sha8(DATASET_PATH), "git_commit": git_commit()},
              "summary": summarize(rows), "cases": rows}
    path = f"{RESULTS_DIR}/{ts}.json"
    json.dump(result, open(path, "w"), indent=2)
    print(json.dumps(result["summary"], indent=2), f"\nsaved {path}")


if __name__ == "__main__":
    main()
