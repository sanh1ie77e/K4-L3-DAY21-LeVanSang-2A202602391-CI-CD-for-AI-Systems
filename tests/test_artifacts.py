from io import BytesIO
import json
from unittest.mock import Mock

import pytest

from src import artifacts


@pytest.mark.parametrize("f1", [0.64, float("nan"), 1.1])
def test_rejected_candidate_cannot_replace_current_model(monkeypatch, f1):
    client = Mock()
    body = BytesIO(json.dumps({"f1_score": f1}).encode())
    client.get_object.return_value = {"Body": body}
    monkeypatch.setattr(artifacts.boto3, "client", lambda service: client)
    with pytest.raises(ValueError):
        artifacts.publish_candidate("lab-bucket", "artifacts/runs/123-1")
    client.copy_object.assert_not_called()
    assert body.closed


def test_approved_candidate_is_published_from_same_run(monkeypatch):
    client = Mock()
    client.get_object.return_value = {"Body": BytesIO(b'{"f1_score": 0.65}')}
    monkeypatch.setattr(artifacts.boto3, "client", lambda service: client)
    artifacts.publish_candidate("lab-bucket", "artifacts/runs/123-2")
    assert client.head_object.call_count == 3
    assert client.copy_object.call_count == 3
    client.copy_object.assert_any_call(
        Bucket="lab-bucket", Key="artifacts/current/model.joblib",
        CopySource={"Bucket": "lab-bucket", "Key": "artifacts/runs/123-2/model.joblib"},
    )


def test_incomplete_candidate_does_not_publish(monkeypatch):
    client = Mock()
    client.get_object.return_value = {"Body": BytesIO(b'{"f1_score": 0.8}')}
    client.head_object.side_effect = [None, None, OSError("Missing detail report")]
    monkeypatch.setattr(artifacts.boto3, "client", lambda service: client)
    with pytest.raises(OSError):
        artifacts.publish_candidate("lab-bucket", "artifacts/runs/123-1")
    client.copy_object.assert_not_called()


@pytest.mark.parametrize("prefix", ["artifacts/current", "artifacts/runs/", "artifacts/runs/../current"])
def test_candidate_prefix_cannot_point_to_current_model(prefix):
    with pytest.raises(ValueError):
        artifacts.validate_prefix(prefix)
