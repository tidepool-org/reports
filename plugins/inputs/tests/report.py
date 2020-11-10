"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from typing import List
import xml.etree.ElementTree as ET

from .suite import TestSuite
from .case import TestCase

class TestReport():
    def __init__(self, report: str):
        self.root = ET.fromstring(report)

    @property
    def test_suites(self) -> List[TestSuite]:
        return [ TestSuite(suite) for suite in self.root.findall('.//testsuite') ]

    @property
    def test_cases(self) -> List[TestCase]:
        return [ TestCase(case) for case in self.root.findall('.//testcase') ]
