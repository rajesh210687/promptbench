"""Run the prompt under test against a single ticket."""
import json
import time

import anthropic

from config import TARGET_MODEL

client = anthropic.Anthropic(max_retries=0)  # we handle retries ourselves


def _retryable(e):
    return isinstance(e, anthropic.RateLimitError) or (
        isinstance(e, anthropic.APIStatusError) and e.status_code in (429, 529))


def create_with_retry(**kwargs):
    """messages.create with up to 3 retries (backoff) on rate-limit/overload only."""
    for attempt in range(4):
        try:
            return client.messages.create(**kwargs)
        except anthropic.APIStatusError as e:
            if not _retryable(e) or attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))


def run_case(ticket, prompt_text):
    # No temperature: Claude 5.x rejects non-default sampling params. Thinking is off so
    # the 300-token budget goes to the JSON reply.
    resp = create_with_retry(model=TARGET_MODEL, system=prompt_text, max_tokens=300,
                             thinking={"type": "disabled"}, messages=[{"role": "user", "content": ticket}])
    text = "".join(b.text for b in resp.content if b.type == "text")
    try:
        out = json.loads(text)
        if not isinstance(out, dict):
            raise ValueError("not an object")
        return out
    except ValueError:
        return {"error": "invalid_json", "raw": text}


if __name__ == "__main__":
    from config import DATASET_PATH, PROMPT_PATH
    prompt = open(PROMPT_PATH).read()
    for line in list(open(DATASET_PATH))[:3]:
        case = json.loads(line)
        out = run_case(case["ticket"], prompt)
        print(case["id"], "expected:", case["expected_category"], case["expected_urgency"], "| actual:", out)
