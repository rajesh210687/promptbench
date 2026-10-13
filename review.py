"""Interactive review of data/golden.jsonl. Enter=accept, e=edit in $EDITOR, d=delete, q=quit."""
import json
import os
import subprocess
import tempfile

from config import DATASET_PATH


def load():
    return [json.loads(l) for l in open(DATASET_PATH) if l.strip()]


def save(cases):
    with open(DATASET_PATH, "w") as f:
        f.writelines(json.dumps(c) + "\n" for c in cases)


def edit(case):
    with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tmp:
        json.dump(case, tmp, indent=2)
    try:
        subprocess.run([os.environ.get("EDITOR", "vi"), tmp.name], check=True)
        return json.load(open(tmp.name))
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"edit discarded: {e}")
        return None
    finally:
        os.unlink(tmp.name)


def main():
    cases = load()
    todo = [c["id"] for c in cases if c.get("reviewed") is not True and not c.get("delete")]
    for n, cid in enumerate(todo, 1):
        i = next(i for i, c in enumerate(cases) if c["id"] == cid)
        c = cases[i]
        print(f"\n--- {cid} ({n}/{len(todo)} left) tags={c['tags']} ---\n{c['ticket']}")
        print(f"category={c['expected_category']} urgency={c['expected_urgency']}")
        print(f"key_facts={c['key_facts']}\nnotes={c['notes']!r}")
        while True:
            key = input("[Enter]=accept  e=edit  d=delete  q=quit > ").strip().lower()
            if key in ("", "e", "d", "q"):
                break
        if key == "q":
            return
        if key == "d":
            c["delete"] = True
        else:
            if key == "e":
                c = edit(c)
                if c is None:
                    continue
            c["reviewed"] = True
        cases[i] = c
        save(cases)
    print("All cases reviewed.")


if __name__ == "__main__":
    main()
