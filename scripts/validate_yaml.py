#!/usr/bin/env python3
from pathlib import Path
import sys
import yaml

root = Path(__file__).resolve().parents[1]
errors = []
for path in sorted((root / "kestra" / "flows").rglob("*.yml")):
    try:
        with path.open("r", encoding="utf-8") as handle:
            yaml.safe_load(handle)
    except Exception as exc:
        errors.append((path, exc))

if errors:
    for path, exc in errors:
        print(f"[ERROR] {path}: {exc}", file=sys.stderr)
    sys.exit(1)
print("YAML syntax OK")
