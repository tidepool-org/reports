"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from .issue import JiraIssue

class JiraTest(JiraIssue):
    @property
    def executions(self):
        return [ ]
