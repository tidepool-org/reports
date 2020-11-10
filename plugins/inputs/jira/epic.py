"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from .issue import JiraIssue

class JiraEpic(JiraIssue):
    @property
    def stories(self):
        return [ story for story in self.jira.stories.values() if story.epic_key == self.key ]
