"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
import logging
from .issue import JiraIssue

logger = logging.getLogger(__name__)

class JiraStory(JiraIssue):
    @property
    def requirements(self):
        return self.rendered_fields.get(self.jira.fields['functional_requirements']) or self.raw_requirements

    @property
    def raw_requirements(self):
        return self.markdown.convert(self.fields.get(self.jira.fields['functional_requirements'], ''))

    @property
    def done_criteria(self):
        return self.rendered_fields.get(self.jira.fields['done_criteria']) or self.raw_done_criteria

    @property
    def raw_done_criteria(self):
        return self.markdown.convert(self.fields.get(self.jira.fields['done_criteria'], ''))

    @property
    def test_strategy(self):
        return self.rendered_fields.get(self.jira.fields['test_strategy']) or self.raw_test_strategy

    @property
    def raw_test_strategy(self):
        return self.markdown.convert(self.fields.get(self.jira.fields['test_strategy'], ''))
