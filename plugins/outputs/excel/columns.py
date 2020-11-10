"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from typing import List

from .column import Column

class Columns(dict):
    def __init__(self, columns: List[dict], row: int = 0):
        for i, column in enumerate(columns):
            col = Column(row = row, column = i, **column)
            self[col.column] = col
            self[col.key] = col
        self.row = row

    @property
    def ordered(self):
        return sorted([ column for key, column in self.items() if isinstance(key, int) ], key = lambda col: col.column)

    def __len__(self):
        return len(self.ordered)

    @property
    def first(self):
        return 0

    @property
    def last(self):
        return len(self) - 1

    def find_all(self, *names: List[str]) -> List[Column]:
        return [ column for key, column in self.items() if isinstance(key, str) and column.key in names ]
