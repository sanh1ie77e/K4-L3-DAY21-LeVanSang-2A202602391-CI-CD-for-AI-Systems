import json
from pathlib import Path
import subprocess
import sys

import pytest

from src.quality_gate import check_quality


@pytest.mark.parametrize("f1", [0.65, 0.8, 1.0, "0.65"])
def test_accepts_threshold_and_above(f1):
    assert check_quality(f1) == float(f1)


@pytest.mark.parametrize("f1", [0.0, 0.649999, float("nan"), float("inf"), -0.1, 1.1, "", None])
def test_blocks_low_or_invalid_f1(f1):
    with pytest.raises((ValueError, TypeError)):
        check_quality(f1)


@pytest.mark.parametrize("f1,exit_code", [(0.64, 1), (0.65, 0)])
def test_gate_cli_uses_f1_even_when_accuracy_is_high(tmp_path, f1, exit_code):
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"f1_score": f1, "accuracy": 0.99}), encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "src/quality_gate.py"
    result = subprocess.run([sys.executable, str(script), str(report)], capture_output=True, text=True)
    assert result.returncode == exit_code
    assert ("PASSED" if exit_code == 0 else "Release blocked") in result.stdout + result.stderr
