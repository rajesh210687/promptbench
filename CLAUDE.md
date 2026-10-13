# promptbench

Minimal harness for measuring whether a prompt change made a support-ticket triage prompt better or worse.
The prompt under test (`prompts/triage.txt`) returns JSON: category, urgency, summary.
Scoring is exact match for category/urgency plus an LLM judge (1-5) for the summary; a case passes if
both exact checks pass and judge score >= `PASS_THRESHOLD`.

## Layout
- `config.py` models, paths, pass threshold
- `prompts/triage.txt` prompt under test
- `data/golden.jsonl` 50 labelled cases; `data/calibration.jsonl` your judge-calibration grades
- `run_prompt.py` `run_case(ticket, prompt_text)`; shared retry helper
- `judge.py` `check_exact`, `judge_summary`, `score_case`
- `review.py` interactive dataset review (Enter accept, e edit, d delete, q quit)
- `calibrate.py` compare judge vs your grades on 12 cases
- `run_eval.py` full run -> `results/<timestamp>.json`
- `report.py` compare two runs -> `reports/<timestamp>.md`, exit 1 on regressions

## Running
    pip install -r requirements.txt        # needs ANTHROPIC_API_KEY
    python review.py                       # once, to approve the dataset
    python calibrate.py                    # aim for >= 75% within-1 agreement
    python run_eval.py --label "v1 baseline"
    python report.py                       # newest two results, or: python report.py old.json new.json

## Rules
- `anthropic` is the only dependency.
- Scripts stay under 150 lines.
- Never edit `data/golden.jsonl` unless asked.

## Notes
- No `temperature` is sent: the SDK has no such argument and Claude 5.x rejects non-default sampling.
  Runs are therefore not guaranteed identical, so measure the noise floor before trusting small diffs.
- Target runs with thinking disabled; the judge uses `between_tools` (Sonnet 5.5 rejects `disabled`).
- Cases marked `"delete": true` by review.py are skipped by run_eval.py.
- Noise floor (two unchanged runs, flipped cases): NOT YET MEASURED.
