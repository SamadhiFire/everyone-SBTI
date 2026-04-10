#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
TARGET = BASE_DIR / "fixtures" / "exes" / "demo-ex"


def main() -> int:
    command = [
        sys.executable,
        str(BASE_DIR / "scripts" / "generate_sbti_report.py"),
        "--target",
        str(TARGET),
        "--mode",
        "file",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    payload = json.loads((TARGET / "sbti-report.json").read_text(encoding="utf-8"))
    assert (TARGET / "sbti-report.html").exists(), "sbti-report.html missing"
    assert payload["result"]["type"], "result.type missing"
    assert len(payload["answers"]) >= 31, "expected questionnaire answers"
    print(completed.stdout.strip())
    print(json.dumps({"type": payload["result"]["type"], "target": payload["target"]["name"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
