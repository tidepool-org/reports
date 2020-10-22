from functools import cached_property # import functools
from .base import JiraBase

class JiraLink(JiraBase):
    def __init__(self, link, jira):
        super().__init__(jira)
        self.link = link

    @property
    def direction(self):
        if 'inwardIssue' in self.link:
            return 'inward'
        elif 'outwardIssue' in self.link:
            return 'outward'
        raise NotImplementedError

    @property
    def issue(self):
        if 'inwardIssue' in self.link:
            return self.link['inwardIssue']
        elif 'outwardIssue' in self.link:
            return self.link['outwardIssue']
        raise NotImplementedError

    @property
    def fields(self):
        return self.issue['fields']
        
    @property
    def type(self):
        return self.fields['issuetype']['name']

    @property
    def link_type(self):
        return self.link['type']['name']

    @property
    def summary(self):
        return self.raw_summary

    @property
    def raw_summary(self):
        return self.fields['summary']

    @property
    def inwardType(self):
        return self.link['type']['inward']

    @property
    def outwardType(self):
        return self.link['type']['outward']

    @cached_property
    def full_issue(self):
        if self.outwardType in [ 'is mitigated by', 'defines', 'created' ]:
            return self.jira.get_issue(self.key, 'JiraIssue')
        elif self.outwardType in [ 'mitigates', 'verifies' ]:
            return self.jira.get_issue(self.key, 'JiraRisk')
        elif self.outwardType in [ 'is defined by' ]:
            return self.jira.get_issue(self.key, 'JiraRequirement')
        elif self.outwardType in [ 'is tested by' ]:
            return self.jira.get_issue(self.key, 'JiraTest')
        return self.jira.get_issue(self.key, 'JiraIssue')

    @property
    def status(self):
        return self.full_issue.status

    @property
    def status_category(self):
        return self.full_issue.status_category

    @property
    def resolution(self):
        return self.full_issue.resolution

    @property
    def harm(self):
        return self.full_issue.harm

    @property
    def tests(self):
        return self.full_issue.tests
