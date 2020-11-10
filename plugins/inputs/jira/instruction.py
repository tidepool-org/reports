"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from .issue import JiraIssue

class JiraInstruction(JiraIssue):
    def publication_date(self):
        return None
