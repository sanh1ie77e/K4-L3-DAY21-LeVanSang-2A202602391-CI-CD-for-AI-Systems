from unittest.mock import Mock

import joblib
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src import serve


@pytest.fixture
def client(monkeypatch):
    model = Mock()
    model.feature_names_in_ = np.array(serve.FEATURE_NAMES)
    model.predict.return_value = np.array([1])
    monkeypatch.setattr(serve, "load_model", lambda: model)
    with TestClient(serve.app) as test_client:
        yield test_client, model


def test_healthz(client):
    test_client, _ = client
    response = test_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("prediction,label", [(0, "thu_nhap_thap"), (1, "thu_nhap_cao")])
def test_score_labels_and_feature_order(client, prediction, label):
    test_client, model = client
    model.predict.return_value = np.array([prediction])
    features = [28, 2, 14, 2, 11, 0, 1, 0, 0, 45]
    response = test_client.post("/score", json={"features": features})
    assert response.status_code == 200
    assert response.json() == {"prediction": prediction, "label": label}
    sample = model.predict.call_args.args[0]
    assert list(sample.columns) == serve.FEATURE_NAMES
    assert sample.iloc[0].tolist() == features


@pytest.mark.parametrize("features", [[], [1] * 9, [1] * 11])
def test_wrong_feature_count(client, features):
    test_client, model = client
    assert test_client.post("/score", json={"features": features}).status_code == 400
    model.predict.assert_not_called()


def test_invalid_payload(client):
    test_client, _ = client
    assert test_client.post("/score", json={"features": ["bad"] * 10}).status_code == 422


def test_not_ready():
    with pytest.raises(serve.HTTPException) as exc:
        serve.healthz()
    assert exc.value.status_code == 503


def test_download_from_s3(monkeypatch, tmp_path):
    destination = tmp_path / "models/model.joblib"
    monkeypatch.setenv("ARTIFACT_BUCKET", "test-bucket")
    monkeypatch.setenv("MODEL_PATH", str(destination))
    client = Mock()
    client.download_file.side_effect = lambda bucket, key, filename: joblib.dump({"model": "test"}, filename)
    monkeypatch.setattr(serve.boto3, "client", lambda service: client)
    assert serve.load_model() == {"model": "test"}
    client.download_file.assert_called_once_with(
        "test-bucket", "artifacts/current/model.joblib", str(destination.with_suffix(".download"))
    )
    assert destination.is_file()
    assert not destination.with_suffix(".download").exists()


def test_failed_s3_download_preserves_existing_model(monkeypatch, tmp_path):
    destination = tmp_path / "model.joblib"
    joblib.dump({"model": "existing"}, destination)
    monkeypatch.setenv("ARTIFACT_BUCKET", "test-bucket")
    monkeypatch.setenv("MODEL_PATH", str(destination))
    client = Mock()

    def interrupted_download(bucket, key, filename):
        with open(filename, "wb") as partial:
            partial.write(b"incomplete")
        raise OSError("Interrupted S3 download")

    client.download_file.side_effect = interrupted_download
    monkeypatch.setattr(serve.boto3, "client", lambda service: client)
    with pytest.raises(OSError, match="Interrupted"):
        serve.download_model()
    assert joblib.load(destination) == {"model": "existing"}
    assert not destination.with_suffix(".download").exists()
