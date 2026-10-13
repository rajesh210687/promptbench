"""Compare two eval runs (newest two by default). Exit 1 if any case regressed."""
import glob
import json
import sys

from config import REPORTS_DIR, RESULTS_DIR


def fmt(v):
    return "n/a" if v is None else f"{v:.2f}" if isinstance(v, float) else str(v)


def case_block(cid, old, new):
    return (f"### {cid}  tags: {', '.join(new['tags'])}\n- old: `{json.dumps(old['output'])}` (judge {old['judge_score']})\n"
            f"- new: `{json.dumps(new['output'])}` (judge {new['judge_score']})\n"
            f"- exact: category_ok {old['category_ok']}→{new['category_ok']}, urgency_ok {old['urgency_ok']}→{new['urgency_ok']}\n"
            f"- new judge reasoning: {new['judge_reasoning']}\n")


def main(argv):
    paths = argv[:2] if len(argv) >= 2 else sorted(glob.glob(f"{RESULTS_DIR}/*.json"))[-2:]
    if len(paths) < 2:
        sys.exit("Need two result files in results/ (or pass two paths).")
    old, new = (json.load(open(p)) for p in paths)
    if old["meta"]["dataset_sha"] != new["meta"]["dataset_sha"]:
        sys.exit(f"WARNING: dataset_sha differs ({old['meta']['dataset_sha']} vs {new['meta']['dataset_sha']}); "
                 "the runs are not comparable. Re-run the older prompt on the current dataset.")
    oc, nc = ({c["id"]: c for c in r["cases"]} for r in (old, new))
    ids = sorted(set(oc) & set(nc))
    reg = [i for i in ids if oc[i]["passed"] and not nc[i]["passed"]]
    imp = [i for i in ids if nc[i]["passed"] and not oc[i]["passed"]]
    shifts = [i for i in ids if oc[i]["passed"] == nc[i]["passed"] and oc[i]["judge_score"] is not None
              and nc[i]["judge_score"] is not None and abs(oc[i]["judge_score"] - nc[i]["judge_score"]) >= 2]
    L = ["# Eval comparison", ""]
    for name, r in (("Old", old), ("New", new)):
        m = r["meta"]
        L.append(f"- **{name}**: label `{m['label']}`, {m['timestamp']}, prompt_sha `{m['prompt_sha']}`")
    L += ["", "## Summary", "", "| metric | old | new | change |", "|---|---|---|---|"]
    for k in new["summary"]:
        o, n = old["summary"][k], new["summary"][k]
        L.append(f"| {k} | {fmt(o)} | {fmt(n)} | {fmt(n - o) if None not in (o, n) else 'n/a'} |")
    L += ["", f"## Regressions ({len(reg)})", ""] + [case_block(i, oc[i], nc[i]) for i in reg]
    L += [f"## Improvements ({len(imp)})", ""] + [case_block(i, oc[i], nc[i]) for i in imp]
    L += [f"## Score shifts ({len(shifts)})", ""]
    L += [f"- {i}: judge {oc[i]['judge_score']}→{nc[i]['judge_score']} (both {'pass' if nc[i]['passed'] else 'fail'}) "
          f"new reasoning: {nc[i]['judge_reasoning']}" for i in shifts]
    L += ["", "## Pass rate by tag", "", "| tag | n | old | new |", "|---|---|---|---|"]
    for t in sorted({t for i in ids for t in nc[i]["tags"]}):
        tid = [i for i in ids if t in nc[i]["tags"]]
        L.append(f"| {t} | {len(tid)} | {sum(oc[i]['passed'] for i in tid) / len(tid):.0%} | "
                 f"{sum(nc[i]['passed'] for i in tid) / len(tid):.0%} |")
    text = "\n".join(L) + "\n"
    open(f"{REPORTS_DIR}/{new['meta']['timestamp']}.md", "w").write(text)
    print(text)
    return 1 if reg else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
