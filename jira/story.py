import logging
from .issue import JiraIssue

logger = logging.getLogger(__name__)

class JiraStory(JiraIssue):
    @property
    def epic_key(self):
        return self.fields[self.jira.fields['epic_key']]

    @property
    def requirements(self):
        return self.rendered_fields[self.jira.fields['functional_requirements']] or self.raw_requirements

    @property
    def raw_requirements(self):
        return self.markdown.convert(self.fields[self.jira.fields['functional_requirements']] or '')

    @property
    def done_criteria(self):
        return self.rendered_fields[self.jira.fields['done_criteria']] or self.raw_done_criteria

    @property
    def raw_done_criteria(self):
        return self.markdown.convert(self.fields[self.jira.fields['done_criteria']] or '')

    @property
    def test_strategy(self):
        return self.rendered_fields[self.jira.fields['test_strategy']] or self.raw_test_strategy

    @property
    def raw_test_strategy(self):
        return self.markdown.convert(self.fields[self.jira.fields['test_strategy']] or '')
