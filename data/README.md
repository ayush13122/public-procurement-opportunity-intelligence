# Data handling rules

- `raw/`: original downloads or manually collected raw snapshots. Do not edit in place.
- `processed/`: cleaned, normalized tables produced by scripts.
- `metadata/source_register.csv`: source URL, access date, method, rights/constraints notes, and fields collected.
- Keep source evidence for every record. If a value is inferred or manually categorized, record the rule and mark it as derived.
- Never fill a missing tender value with a guessed value. Use null and explain the limitation.
- Do not include credentials, personal data, or sensitive bid information.
