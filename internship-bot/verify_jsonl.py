import json
import pathlib

files = [
    "data/training_data_scorer.jsonl",
    "data/training_data_coverletter.jsonl",
]

for f in files:
    path = pathlib.Path(f)
    if not path.exists():
        print(f"MISSING: {f}")
        continue
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    errors = []
    for i, line in enumerate(lines, 1):
        try:
            obj = json.loads(line)
            if "text_input" not in obj or "output" not in obj:
                errors.append(f"Line {i}: missing keys")
        except Exception as e:
            errors.append(f"Line {i}: {e}")
    status = "PASS" if not errors else "FAIL"
    err_detail = str(errors[:3]) if errors else "all valid"
    print(f"[{status}] {f} -- {len(lines)} records -- {err_detail}")
