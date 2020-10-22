from .base import JiraBase
from .link import JiraLink

class JiraIssue(JiraBase):
    def __init__(self, issue, jira):
        super().__init__(jira)
        self.issue = issue

    @property
    def type(self):
        return self.fields['issuetype']['name'] or ''

    @property
    def resolution(self):
        res = self.fields['resolution']
        if res:
            return res['name'] or ''
        return ''

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
        return self.issue['fields'] or {}

    @property
    def rendered_fields(self):
        return self.issue.get('renderedFields') or {}

    @property
    def links(self):
        return [ JiraLink(link, self.jira) for link in self.fields['issuelinks'] ]

    @property
    def stories(self):
        return [ link for link in self.links if link.is_story and link.link_type != 'Risk Mitigation' ]

    @property
    def tests(self):
        return [ link for link in self.links if link.is_test ]

    @property
    def risks(self):
        return [ link for link in self.links if link.is_risk or link.link_type == 'Risk Mitigation' ]
