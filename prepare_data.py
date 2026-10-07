"""Prepare the fixed Day 21 split from the official UCI Adult archive."""

import argparse
from io import BytesIO
from pathlib import Path
import urllib.request
from zipfile import ZipFile

import pandas as pd

DATASET_URL = 'https://archive.ics.uci.edu/static/public/2/adult.zip'
RAW_COLUMNS = [
    'age', 'workclass', 'fnlwgt', 'education', 'education_num', 'marital_status',
    'occupation', 'relationship', 'race', 'sex', 'capital_gain', 'capital_loss',
    'hours_per_week', 'native_country', 'income',
]
FEATURE_COLUMNS = [
    'age', 'workclass', 'education_num', 'marital_status', 'occupation',
    'relationship', 'sex', 'capital_gain', 'capital_loss', 'hours_per_week',
]
CATEGORICAL_COLUMNS = ['workclass', 'marital_status', 'occupation', 'relationship', 'sex']


def prepare_data(raw_dir=None):
    if raw_dir:
        train_source = Path(raw_dir) / 'adult.data'
        test_source = Path(raw_dir) / 'adult.test'
    else:
        cached = Path('outputs/raw-adult.zip')
        if not cached.exists():
            print(f'Downloading official UCI archive: {DATASET_URL}', flush=True)
            cached.parent.mkdir(parents=True, exist_ok=True)
            request = urllib.request.Request(DATASET_URL, headers={'User-Agent': 'Day21-MLOps-Lab'})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            # Validate before saving, so an interrupted download cannot become a cache.
            with ZipFile(BytesIO(payload)) as archive:
                archive.getinfo('adult.data')
                archive.getinfo('adult.test')
            cached.write_bytes(payload)
        with ZipFile(cached) as archive:
            train_source = BytesIO(archive.read('adult.data'))
            test_source = BytesIO(archive.read('adult.test'))

    def load(source, skiprows):
        return pd.read_csv(source, header=None, names=RAW_COLUMNS, skiprows=skiprows,
                           skipinitialspace=True, na_values='?')

    df_train, df_test = load(train_source, 0), load(test_source, 1)
    df_test['income'] = df_test['income'].str.rstrip('.')
    df = pd.concat([df_train, df_test], ignore_index=True).dropna().reset_index(drop=True)
    for column in CATEGORICAL_COLUMNS:
        df[column] = pd.Categorical(df[column]).codes
    df['target'] = (df['income'] == '>50K').astype(int)
    df = df[FEATURE_COLUMNS + ['target']].sample(frac=1, random_state=42).reset_index(drop=True)
    n_holdout = 500
    n_half = (len(df) - n_holdout) // 2
    if len(df) != 45222 or n_half != 22361:
        raise ValueError(f'Unexpected Adult dataset size after cleaning: {len(df)}')
    splits = {
        'train_batch1.csv': df.iloc[n_holdout:n_holdout + n_half],
        'holdout.csv': df.iloc[:n_holdout],
        'train_batch2.csv': df.iloc[n_holdout + n_half:n_holdout + 2 * n_half],
    }
    Path('data').mkdir(exist_ok=True)
    for filename, dataset in splits.items():
        dataset.to_csv(Path('data') / filename, index=False)
        print(f'{filename:16}: {len(dataset)} mau')
    print(f"Ty le lop >50K   : {df['target'].mean():.1%}")
    return splits


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--raw-dir', help='Offline directory containing adult.data and adult.test')
    prepare_data(parser.parse_args().raw_dir)
