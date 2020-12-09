"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
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
        res = self.fields.get('resolution')
        if res:
            return res.get('name', '')
        return ''

    @property
    def description(self) -> str:
        return self.rendered_fields.get('description') or self.raw_description

    @property
    def raw_description(self) -> str:
        return self.markdown.convert(self.fields.get('description') or '')

    @property
    def fix_versions(self) -> List[str]:
        return [ version['name'] for version in self.fields['fixVersions'] ]

    @property
    def affects_versions(self) -> List[str]:
        return [ version['name'] for version in self.fields['versions'] ]

    @property
    def components(self) -> List[str]:
        return [ component['name'] for component in self.fields['components'] ]

    @property
    def links(self) -> List[JiraLink]:
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
