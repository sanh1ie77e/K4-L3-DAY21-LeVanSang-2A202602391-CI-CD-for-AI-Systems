"""Run the three configurations required by Day 21 and keep the winner."""

import json
from pathlib import Path
import shutil

import yaml
from src.train import F1_THRESHOLD, train

CONFIGURATIONS = [
    {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 3},
    {"n_estimators": 50, "learning_rate": 0.05, "max_depth": 2},
    {"n_estimators": 200, "learning_rate": 0.1, "max_depth": 5},
]


def run_experiments():
    results = []
    for number, params in enumerate(CONFIGURATIONS, start=1):
        # Read the edited params.yaml, matching the manual lab procedure.
        Path("params.yaml").write_text(yaml.safe_dump(params, sort_keys=False), encoding="utf-8")
        with open("params.yaml", encoding="utf-8") as f:
            current_params = yaml.safe_load(f)
        output_dir = f"outputs/experiments/run{number}"
        model_dir = f"models/experiments/run{number}"
        train(current_params, output_dir=output_dir, model_dir=model_dir,
              run_name=f"step1-run{number}", stage="step1")
        report = json.loads(Path(output_dir, "report.json").read_text(encoding="utf-8"))
        results.append({"number": number, **report})
    best = max(results, key=lambda result: result["f1_score"])
    Path("outputs/experiments.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if best["f1_score"] < F1_THRESHOLD:
        raise SystemExit("No run passed F1 >= 0.65; try additional configurations before deployment")
    Path("params.yaml").write_text(yaml.safe_dump(best["params"], sort_keys=False), encoding="utf-8")
    for name in ["report.json", "detail.txt"]:
        shutil.copyfile(f"outputs/experiments/run{best['number']}/{name}", f"outputs/{name}")
    shutil.copyfile(f"models/experiments/run{best['number']}/model.joblib", "models/model.joblib")
    print(f"Selected run {best['number']}: {best['params']} | F1={best['f1_score']:.6f}")
    return results


if __name__ == "__main__":
    run_experiments()
