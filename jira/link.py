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

    @property
    def full_issue(self):
        return self.jira.all_issues[self.key]

    @property
    def tests(self):
        return self.full_issue.tests
