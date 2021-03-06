"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from typing import NamedTuple

class Column(NamedTuple):
    column: int
    width: int
    row: int
    key: str
    label: str

    def __int__(self) -> int:
        return self.column
