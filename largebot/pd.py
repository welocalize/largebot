import pandas as pd
import numpy as np

from typing import Optional, Union
from welo365.welo365 import O365Account, WorkBook, WorkSheet, Range


class O365DataFrame(pd.DataFrame):
    _metadata = ['ws', 'address']
    def __init__(self, data, ws: WorkSheet, index=None, columns=None, dtype=None, copy=True):
        super().__init__(data=data, columns=columns, index=index, dtype=dtype, copy=copy)
        print(self)
        self.ws = ws
        self = self.replace(
            to_replace=[''],
            value=np.nan
        ).dropna(
            subset=[columns[0]]
        ).dropna(
            axis=1
        ).set_index(
            columns[0]
        )
        self = self.where(pd.notnull(self), '')
        self.address = f"B2:{'ABCDEFGHIJKLMNOPQRSTUVWXYZ'[len(self.columns)]}{len(self) + 1}"

    @classmethod
    def _internal_ctor(cls, *args, **kwargs):
        kwargs['ws'] = None
        return cls(*args, **kwargs)

    @property
    def _constructor(self):
        return O365DataFrame._internal_ctor

    @property
    def data(self):
        return self.values.tolist()

    def publish(self):
        _range = self.ws.get_range(self.address)
        _range.values = self.values.tolist()
        _range.update()


def get_df(worksheet: WorkSheet, index_col: Optional[Union[int, str]] = None):
    _range = worksheet.get_used_range()
    columns, *values = _range.values
    df = pd.DataFrame(values, columns=columns)
    df = df.replace(
        to_replace=[''],
        value=np.nan
    )
    index = len(columns)
    for i, col in enumerate(columns):
        if df[col].dropna().empty:
            if i == index + 1:
                break
            index = i
    df = df[columns[0:index]]
    df = df.dropna(
        subset=[columns[0]]
    )
    if index_col is not None:
        index_col = columns[index_col] if isinstance(index_col, int) else index_col
        df = df.set_index(index_col)
    return df.where(pd.notnull(df), '')
