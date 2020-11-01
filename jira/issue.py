import logging
from typing import List
from .base import JiraBase
from .link import JiraLink

logger = logging.getLogger(__name__)

class JiraIssue(JiraBase):
    @property
    def epic_key(self):
        return self.fields[self.jira.fields['epic_key']]

    @property
    def resolution(self) -> str:
        res = self.fields['resolution']
        if res:
            return res.get('name', '')
        return ''

    @property
    def description(self) -> str:
        return self.rendered_fields['description'] or self.raw_description

    @property
    def raw_description(self) -> str:
        return self.markdown.convert(self.fields['description'] or '')

    @property
    def fix_versions(self) -> List[str]:
        return [ fix_version['name'] for fix_version in self.fields['fixVersions'] ]

    @property
    def affects_version(self):
        return [ affects_version['name'] for affects_version in self.fields['versions'] ]

    @property
    def links(self):
        return [ JiraLink(link, self.jira) for link in self.fields['issuelinks'] ]

    @property
    def linked(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links ]

    @property
    def stories(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links if link.is_story ]

    @property
    def tests(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links if link.is_test ]

    @property
    def risks(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links if link.is_risk ]

    @property
    def relates_to(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links if link.relates ]

    @property
    def defines(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links if link.defines ]

    @property
    def defined_by(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links if link.is_defined_by ]

    @property
    def mitigated_by(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links if link.is_mitigated_by ]
