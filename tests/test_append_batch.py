import pandas as pd
import pytest

from append_batch import append_batch


def test_append_once_and_reject_replay(tmp_path):
    train_path, new_path = tmp_path / "train.csv", tmp_path / "new.csv"
    original = pd.DataFrame({"target": [0] * 22361})
    fresh = pd.DataFrame({"target": [1] * 22361})
    original.to_csv(train_path, index=False)
    fresh.to_csv(new_path, index=False)
    assert append_batch(train_path, new_path) == 44722
    before = train_path.read_bytes()
    with pytest.raises(ValueError, match="already have been appended"):
        append_batch(train_path, new_path)
    assert train_path.read_bytes() == before
