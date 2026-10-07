"""Fail closed unless positive-class F1 reaches the lab threshold."""

import argparse
import json
import math

F1_THRESHOLD = 0.65


def check_quality(f1, threshold=F1_THRESHOLD):
    value = float(f1)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("f1_score must be finite and between 0 and 1")
    if value < threshold:
        raise ValueError(f"FAILED: f1_score {value:.4f} < {threshold:.2f}. Release blocked.")
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("report", nargs="?", default="outputs/report.json")
    args = parser.parse_args()
    try:
        with open(args.report, encoding="utf-8") as f:
            value = check_quality(json.load(f)["f1_score"])
    except (ValueError, TypeError, KeyError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    print(f"PASSED: f1_score {value:.4f} >= {F1_THRESHOLD:.2f}")
