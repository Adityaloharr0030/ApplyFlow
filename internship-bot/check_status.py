checks = {
    "agent/ai_client.py": [
        ("model_type param in get_ai_response", "model_type"),
        ("_get_gemini_model() function", "_get_gemini_model"),
        ("TUNED_SCORER_MODEL env var", "TUNED_SCORER_MODEL"),
        ("TUNED_COVER_MODEL env var", "TUNED_COVER_MODEL"),
    ],
    "agent/filter.py": [
        ("model_type=scorer passed", 'model_type="scorer"'),
    ],
    "agent/cover_note.py": [
        ("model_type=cover passed", 'model_type="cover"'),
    ],
    "main.py": [
        ("--test-scoring CLI flag", "--test-scoring"),
        ("test_scoring() function", "def test_scoring()"),
    ],
    ".env.example": [
        ("TUNED_SCORER_MODEL entry", "TUNED_SCORER_MODEL"),
        ("TUNED_COVER_MODEL entry", "TUNED_COVER_MODEL"),
    ],
    "data/training_data_scorer.jsonl": [
        ("file exists", "score"),
    ],
    "data/training_data_coverletter.jsonl": [
        ("file exists", "cover letter"),
    ],
}

all_pass = True
for filepath, items in checks.items():
    print(f"\n[{filepath}]")
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        for label, needle in items:
            found = needle in content
            icon = "OK" if found else "MISSING"
            if not found:
                all_pass = False
            print(f"  [{icon}] {label}")
    except FileNotFoundError:
        print(f"  [MISSING FILE] {filepath}")
        all_pass = False

print("\n" + ("=" * 40))
print("STATUS:", "ALL CHECKS PASS" if all_pass else "SOME CHECKS FAILED")
print("=" * 40)
