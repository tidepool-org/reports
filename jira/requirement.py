from .issue import JiraIssue

class JiraRequirement(JiraIssue):
    @property
    def id(self):
        return self.fields[self.jira.fields['reference_id']] or ''
