"""Measure both batch sizes locally without advancing the DVC data pointer."""

import json
from pathlib import Path
import tempfile

import yaml
from append_batch import append_batch
from src.train import train


def compare_batches():
    with open("params.yaml", encoding="utf-8") as f:
        params = yaml.safe_load(f)
    train(params, output_dir="outputs/batch-comparison/step2",
          model_dir="models/batch-comparison/step2", run_name="local-step2", stage="local-comparison")
    with tempfile.TemporaryDirectory(dir="outputs") as temporary:
        combined_path = str(Path(temporary) / "train_combined.csv")
        append_batch(output_path=combined_path)
        train(params, data_path=combined_path, output_dir="outputs/batch-comparison/step3",
              model_dir="models/batch-comparison/step3", run_name="local-step3", stage="local-comparison")
    comparison = {"source": "local simulation; not GitHub Actions artifacts"}
    for stage in ["step2", "step3"]:
        comparison[stage] = json.loads(Path(f"outputs/batch-comparison/{stage}/report.json").read_text(encoding="utf-8"))
    Path("outputs/batch-comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")
    print(json.dumps(comparison, indent=2))
    return comparison


if __name__ == "__main__":
    compare_batches()
