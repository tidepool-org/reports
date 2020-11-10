"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from .issue import JiraIssue

class JiraUserRequirement(JiraIssue):
    @property
    def id(self):
        return self.fields[self.jira.fields['reference_id']] or ''

    @property
    def risks(self):
        all = set(super().risks)
        # aggregate indirect risks from linked stories
        for story in self.stories:
            all.update(self.jira.get_issue(story.key, JiraIssue).risks)
        return all
