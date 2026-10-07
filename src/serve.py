"""FastAPI serving: download from S3 on startup, or use a local model."""

from contextlib import asynccontextmanager
import math
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
import boto3
import joblib
import pandas as pd
from pydantic import BaseModel

MODEL_KEY = "artifacts/current/model.joblib"
FEATURE_NAMES = [
    "age", "workclass", "education_num", "marital_status", "occupation",
    "relationship", "sex", "capital_gain", "capital_loss", "hours_per_week",
]


def get_model_path():
    default = "~/models/model.joblib" if os.environ.get("ARTIFACT_BUCKET") else "models/model.joblib"
    return Path(os.environ.get("MODEL_PATH", default)).expanduser()


def download_model():
    bucket_name = os.environ.get("ARTIFACT_BUCKET")
    if not bucket_name:
        raise RuntimeError("Set ARTIFACT_BUCKET to download a model from S3")
    destination = get_model_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".download")
    client = boto3.client("s3")
    try:
        client.download_file(bucket_name, MODEL_KEY, str(temporary))
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Downloaded model from s3://{bucket_name}/{MODEL_KEY}")


def load_model():
    if os.environ.get("ARTIFACT_BUCKET"):
        download_model()
    return joblib.load(get_model_path())


@asynccontextmanager
async def lifespan(application):
    # Importing this module does not require cloud credentials or a model file.
    application.state.model = load_model()
    yield
    application.state.model = None


app = FastAPI(title="Adult Income API", lifespan=lifespan)
app.state.model = None


class ScoreRequest(BaseModel):
    features: list[float]


@app.get("/healthz")
def healthz():
    if app.state.model is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    return {"status": "ok"}


@app.post("/score")
def score(req: ScoreRequest):
    if len(req.features) != 10:
        raise HTTPException(status_code=400, detail="Expected 10 features (adult income)")
    if not all(math.isfinite(value) for value in req.features):
        raise HTTPException(status_code=400, detail="Features must be finite numbers")
    model = app.state.model
    if model is None:
        raise HTTPException(status_code=503, detail="Model not ready")
    columns = getattr(model, "feature_names_in_", FEATURE_NAMES)
    sample = pd.DataFrame([req.features], columns=columns)
    pred = int(model.predict(sample)[0])
    return {"prediction": pred, "label": "thu_nhap_cao" if pred == 1 else "thu_nhap_thap"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
