"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from enum import IntEnum 

class JiraRiskScore(IntEnum):
    UNKNOWN = 0
    GREEN = 1
    YELLOW = 2
    RED = 3
