from .base import JiraBase
from .link import JiraLink

class JiraIssue(JiraBase):
    def __init__(self, issue, jira):
        super().__init__(jira)
        self.issue = issue

    @property
    def type(self):
        return self.fields['issuetype']['name']

    @property
    def summary(self):
        return self.raw_summary

    @property
    def raw_summary(self):
        return self.fields['summary'] or ''

    @property
    def description(self):
        return self.rendered_fields['description'] or ''

    @property
    def raw_description(self):
        return self.fields['description'] or ''

    @property
    def fields(self):
        return self.issue['fields']

    @property
    def rendered_fields(self):
        return self.issue['renderedFields']

    @property
    def links(self):
        return [ JiraLink(link, self.jira) for link in self.fields['issuelinks'] ]

    @property
    def stories(self):
        return [ link for link in self.links if link.is_story ]

    @property
    def tests(self):
        return [ link for link in self.links if link.is_test ]

    @property
    def risks(self):
        return [ link for link in self.links if link.is_risk ]
