from .issue import JiraIssue

class JiraInstruction(JiraIssue):
    def publication_date(self):
        return None
