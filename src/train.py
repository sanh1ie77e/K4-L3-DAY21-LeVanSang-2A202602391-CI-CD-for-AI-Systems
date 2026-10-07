"""Train Adult Income and track positive-class F1 with MLflow."""

import json
import os
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import yaml
from mlflow.models import infer_signature
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

F1_THRESHOLD = 0.65
REFERENCE_POSITIVE_RATE = 0.248
DRIFT_THRESHOLD = 0.05  # Five percentage points, not five percent relative.
FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


def configure_tracking():
    """Apply the local artifact root when creating the MLflow experiment."""
    uri = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    mlflow.set_tracking_uri(uri)
    name = os.environ.get("MLFLOW_EXPERIMENT_NAME", "Adult-Income")
    experiment = mlflow.get_experiment_by_name(name)
    if experiment is None:
        artifact_location = None
        if uri.startswith(("sqlite:", "file:")) or "://" not in uri:
            artifact_root = Path(os.environ.get("MLFLOW_ARTIFACT_ROOT", "./mlartifacts"))
            artifact_root.mkdir(parents=True, exist_ok=True)
            artifact_location = artifact_root.resolve().as_uri()
        experiment_id = mlflow.create_experiment(name, artifact_location=artifact_location)
    else:
        experiment_id = experiment.experiment_id
    mlflow.set_experiment(experiment_id=experiment_id)


def read_dataset(csv_path):
    df = pd.read_csv(csv_path)
    expected = set(FEATURE_NAMES + ["target"])
    if df.empty or set(df.columns) != expected:
        raise ValueError(f"{csv_path}: expected 10 Adult features and target, with nonempty data")
    if not all(pd.api.types.is_numeric_dtype(df[col]) for col in df.columns):
        raise ValueError(f"{csv_path}: all columns must be numeric")
    if not np.isfinite(df.to_numpy()).all():
        raise ValueError(f"{csv_path}: missing or nonfinite values")
    if not df["target"].isin([0, 1]).all():
        raise ValueError(f"{csv_path}: target must be 0 or 1")
    return df


def train(
    params: dict,
    data_path: str = "data/train_batch1.csv",
    eval_path: str = "data/holdout.csv",
    *,
    output_dir: str = "outputs",
    model_dir: str = "models",
    run_name: str | None = None,
    stage: str = "training",
) -> float:
    """Fit only the training CSV; evaluate on the fixed holdout and return F1."""
    if Path(data_path).resolve() == Path(eval_path).resolve():
        raise ValueError("Training and holdout paths must be different")
    df_train = read_dataset(data_path)
    df_eval = read_dataset(eval_path)
    X_train, y_train = df_train[FEATURE_NAMES], df_train["target"]
    X_eval, y_eval = df_eval[FEATURE_NAMES], df_eval["target"]
    if y_train.nunique() != 2:
        raise ValueError("Training data must contain both target classes")
    positive_rate = float(y_train.mean())
    drift_detected = abs(positive_rate - REFERENCE_POSITIVE_RATE) > DRIFT_THRESHOLD + 1e-12
    print(f"Train: {len(df_train)} | Holdout: {len(df_eval)} | Positive rate: {positive_rate:.2%}")
    if drift_detected:
        print("WARNING: DATA DRIFT - positive rate differs by more than 5 percentage points from 24.8%")

    output_path, model_path = Path(output_dir), Path(model_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    model_path.mkdir(parents=True, exist_ok=True)
    configure_tracking()
    with mlflow.start_run(run_name=run_name, tags={"stage": stage}) as run:
        mlflow.log_params(params)
        mlflow.log_param("random_state", 42)
        model = GradientBoostingClassifier(**params, random_state=42)
        model.fit(X_train, y_train)
        preds = model.predict(X_eval)
        # Binary F1 for target=1. Do not use macro or weighted averaging.
        f1 = float(f1_score(y_eval, preds))
        acc = float(accuracy_score(y_eval, preds))
        mlflow.log_metrics({"f1_score": f1, "accuracy": acc, "positive_class_ratio": positive_rate})
        mlflow.log_params({"n_train": len(df_train), "n_eval": len(df_eval)})
        mlflow.set_tag("data_drift", str(drift_detected).lower())
        mlflow.sklearn.log_model(
            model, "model", signature=infer_signature(X_eval, preds),
            input_example=X_eval.iloc[:5],
        )
        report = {
            "f1_score": f1, "accuracy": acc, "params": params,
            "n_train": len(df_train), "n_eval": len(df_eval),
            "positive_class_ratio": positive_rate, "data_drift": drift_detected,
            "f1_threshold": F1_THRESHOLD, "quality_gate_passed": f1 >= F1_THRESHOLD,
            "run_id": run.info.run_id,
        }
        (output_path / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        detail = "Confusion matrix (rows=true, columns=predicted; labels=[0, 1]):\n"
        detail += str(confusion_matrix(y_eval, preds, labels=[0, 1])) + "\n\n"
        detail += classification_report(
            y_eval, preds, labels=[0, 1], target_names=["thu_nhap_thap", "thu_nhap_cao"],
            digits=4, zero_division=0,
        )
        (output_path / "detail.txt").write_text(detail, encoding="utf-8")
        joblib.dump(model, model_path / "model.joblib")
        mlflow.log_artifact(str(output_path / "report.json"), artifact_path="evaluation")
        mlflow.log_artifact(str(output_path / "detail.txt"), artifact_path="evaluation")
        print(f"F1: {f1:.4f} | Accuracy: {acc:.4f} | Gate: {'PASSED' if f1 >= F1_THRESHOLD else 'FAILED'}")
    return f1


if __name__ == "__main__":
    with open("params.yaml", encoding="utf-8") as f:
        train(yaml.safe_load(f))
