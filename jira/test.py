from .issue import JiraIssue

class JiraTest(JiraIssue):
    @property
    def executions(self):
        return [ ]
