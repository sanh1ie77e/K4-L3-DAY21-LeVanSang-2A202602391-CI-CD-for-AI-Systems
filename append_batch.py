"""Append batch 2 once; refuse duplicate ingestion or schema mismatch."""

from pathlib import Path
import pandas as pd


def append_batch(train_path='data/train_batch1.csv', new_path='data/train_batch2.csv', output_path=None):
    df_train = pd.read_csv(train_path)
    df_new = pd.read_csv(new_path)
    if list(df_train.columns) != list(df_new.columns):
        raise ValueError('Batch schemas differ; no data was changed')
    if len(df_new) != 22361 or len(df_train) != 22361:
        raise ValueError('Expected two batches of 22361 rows; batch 2 may already have been appended')
    updated = pd.concat([df_train, df_new], ignore_index=True)
    destination = Path(output_path or train_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.tmp.csv')
    updated.to_csv(temporary, index=False)
    temporary.replace(destination)
    print(f'Cap nhat du lieu: {len(df_train)} -> {len(updated)} mau')
    return len(updated)


if __name__ == '__main__':
    append_batch()
