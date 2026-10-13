"""Scoring: exact-match checks for category/urgency, LLM judge for the summary."""
import json

from config import JUDGE_MODEL, PASS_THRESHOLD
from run_prompt import create_with_retry

RUBRIC = """5 = captures every key fact, adds nothing untrue, one clear sentence
4 = captures every key fact, minor wording issues
3 = misses one key fact OR adds a minor detail not in the ticket
2 = misses most key facts or misstates the problem
1 = wrong, empty, or invented content"""

JUDGE_PROMPT = """You grade the one-sentence summary of a customer support ticket.

Ticket:
{ticket}

Key facts a good summary must capture:
{facts}

Candidate summary:
{summary}

Rubric:
{rubric}

Any specific detail (amount, date, order number, outcome) that is not in the ticket counts as invented.
When unsure between two scores, choose the lower one.

Reply with ONLY a JSON object. Write your reasoning first, then the score:
{{"reasoning": "<check each key fact, then check for anything not in the ticket>", "score": <1-5 integer>}}"""


def check_exact(output, case):
    if "error" in output:
        return {"category_ok": False, "urgency_ok": False}
    return {"category_ok": output.get("category") == case["expected_category"],
            "urgency_ok": output.get("urgency") == case["expected_urgency"]}


def judge_summary(output, case):
    if "error" in output:
        return {"reasoning": "target output was invalid JSON; no summary to judge", "score": 1}
    prompt = JUDGE_PROMPT.format(rubric=RUBRIC, ticket=case["ticket"], summary=output.get("summary", ""),
                                 facts="\n".join(f"- {f}" for f in case["key_facts"]))
    resp = create_with_retry(model=JUDGE_MODEL, max_tokens=800, thinking={"type": "between_tools"},
                             messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        data = json.loads(text[text.index("{"):text.rindex("}") + 1])
        return {"reasoning": data["reasoning"], "score": int(data["score"])}
    except (ValueError, KeyError, TypeError):
        return {"reasoning": f"JUDGE_PARSE_ERROR: {text[:300]}", "score": None}


def score_case(output, case):
    exact, judged = check_exact(output, case), judge_summary(output, case)
    passed = (exact["category_ok"] and exact["urgency_ok"]
              and judged["score"] is not None and judged["score"] >= PASS_THRESHOLD)
    return {**exact, "judge_reasoning": judged["reasoning"], "judge_score": judged["score"], "passed": passed}


if __name__ == "__main__":  # sanity check: a faithful and an invented summary for t001
    case = json.loads(open("data/golden.jsonl").readline())
    good = {"category": case["expected_category"], "urgency": case["expected_urgency"],
            "summary": "; ".join(case["key_facts"])}
    bad = {**good, "summary": good["summary"] + ", and wants a $75 refund"}
    for name, out in [("good", good), ("bad", bad)]:
        print(name, judge_summary(out, case))
