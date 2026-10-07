import json
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import accuracy_score, f1_score

from src.train import FEATURE_NAMES, read_dataset, train


def _make_temp_data(tmp_path):
    rng = np.random.default_rng(0)
    X = rng.random((200, len(FEATURE_NAMES)))
    # Minority positive class; accuracy and F1 must not be interchangeable.
    y = (X[:, 0] + X[:, 1] > 1.35).astype(int)
    df = pd.DataFrame(X, columns=FEATURE_NAMES)
    df['target'] = y
    train_path, eval_path = tmp_path / 'train.csv', tmp_path / 'holdout.csv'
    df.iloc[:160].to_csv(train_path, index=False)
    df.iloc[160:].to_csv(eval_path, index=False)
    return str(train_path), str(eval_path)


@pytest.fixture(scope='module')
def trained(tmp_path_factory):
    temporary = tmp_path_factory.mktemp('training')
    train_path, eval_path = _make_temp_data(temporary)
    uri = 'sqlite:///' + (temporary / 'mlflow.db').as_posix()
    with pytest.MonkeyPatch.context() as patch:
        patch.chdir(temporary)
        patch.setenv('MLFLOW_TRACKING_URI', uri)
        patch.setenv('MLFLOW_ARTIFACT_ROOT', str(temporary / 'artifacts'))
        patch.setenv('MLFLOW_EXPERIMENT_NAME', 'Unit-Tests')
        result = train({'n_estimators': 10, 'learning_rate': 0.1, 'max_depth': 2},
                       data_path=train_path, eval_path=eval_path)
    return temporary, result, eval_path, uri


def test_train_returns_float(trained):
    _, result, _, _ = trained
    assert isinstance(result, float)
    assert 0.0 <= result <= 1.0


def test_report_file_created(trained):
    temporary, result, eval_path, uri = trained
    report = json.loads((temporary / 'outputs/report.json').read_text(encoding='utf-8'))
    model = joblib.load(temporary / 'models/model.joblib')
    evaluation = pd.read_csv(eval_path)
    predictions = model.predict(evaluation[FEATURE_NAMES])
    assert report['f1_score'] == result == f1_score(evaluation['target'], predictions)
    assert report['accuracy'] == accuracy_score(evaluation['target'], predictions)
    assert report['n_train'] == 160
    assert report['n_eval'] == 40
    run = mlflow.tracking.MlflowClient(tracking_uri=uri).get_run(report['run_id'])
    assert run.info.status == 'FINISHED'
    assert run.data.metrics['f1_score'] == result
    assert run.data.metrics['accuracy'] == report['accuracy']
    assert run.data.params['n_estimators'] == '10'
    detail = (temporary / 'outputs/detail.txt').read_text(encoding='utf-8')
    assert 'Confusion matrix' in detail
    assert 'precision' in detail and 'recall' in detail and 'thu_nhap_cao' in detail


def test_model_file_created(trained):
    temporary, _, _, _ = trained
    model_path = temporary / 'models/model.joblib'
    assert model_path.is_file()
    model = joblib.load(model_path)
    assert list(model.feature_names_in_) == FEATURE_NAMES
    assert list(model.classes_) == [0, 1]


@pytest.mark.parametrize('invalid_target', [2, -1, 0.5])
def test_invalid_target_rejected(tmp_path, invalid_target):
    train_path, _ = _make_temp_data(tmp_path)
    df = pd.read_csv(train_path)
    df.loc[0, 'target'] = invalid_target
    df.to_csv(train_path, index=False)
    with pytest.raises(ValueError, match='target must be 0 or 1'):
        read_dataset(train_path)


def test_holdout_not_used_as_training(tmp_path):
    train_path, _ = _make_temp_data(tmp_path)
    with pytest.raises(ValueError, match='must be different'):
        train({'n_estimators': 10}, data_path=train_path, eval_path=train_path)
