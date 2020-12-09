"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from abc import ABC, abstractmethod
import markdown

class JiraBase(ABC):
    def __init__(self, issue, jira):
        self.issue = issue
        self.jira = jira
        self.markdown = markdown.Markdown()

    def __eq__(self, other):
        return self.key == other.key

    def __hash__(self):
        return hash(self.key)

    @property
    def full_issue(self):
        # overridden by derived class such as JiraLink
        return self

    @property
    def type(self) -> int:
        return int(self.fields['issuetype']['id'])

    @property
    def key(self) -> str:
        return self.issue['key']

    @property
    def project_key(self) -> str:
        return self.key.split('-')[0]

    @property
    def fields(self) -> dict:
        return self.issue['fields'] or {}

    @property
    def rendered_fields(self) -> dict:
        return self.issue.get('renderedFields') or {}

    @property
    def url(self) -> str:
        return f"{self.jira.config['base_url']}/browse/{self.key}"

    @property
    def icon(self) -> str:
        return self.fields['issuetype']['iconUrl']

    @property
    def status(self) -> str:
        return self.fields['status']['name']

    @property
    def status_category(self) -> str:
        return self.fields['status']['statusCategory']['name']

    @property
    def priority(self) -> str:
        return self.fields['priority']['name']

    @property
    def summary(self):
        return self.raw_summary

    @property
    def raw_summary(self):
        return self.fields['summary']

    def is_a(self, type_name: str) -> bool:
        issue_type = self.jira.issue_types[type_name]
        return self.type in issue_type['ids'] and self.project_key in issue_type['projects']

    @property
    def is_story(self) -> bool:
        return self.is_a('story')

    @property
    def is_bug(self) -> bool:
        return self.is_a('bug')

    @property
    def is_test(self) -> bool:
        return self.is_a('test')

    @property
    def is_risk(self) -> bool:
        return self.is_a('risk')

    @property
    def is_func_requirement(self) -> bool:
        return self.is_a('func_requirement')

    @property
    def is_user_requirement(self) -> bool:
        return self.is_a('user_requirement')

    @property
    def is_instruction(self) -> bool:
        return self.is_a('instruction')

    @property
    def is_junk(self) -> bool:
        return self.resolution in self.jira.junk_resolution

    @property
    def is_done(self) -> bool:
        return self.status in self.jira.done_status

    @property
    def is_blocked(self) -> bool:
        return self.status in self.jira.blocked_status

    @property
    def is_device_qualification(self):
        return set(self.components) & set(self.jira.device_qual_component)
