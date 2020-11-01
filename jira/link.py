from functools import cached_property # import functools
from .base import JiraBase
from .link_dir import JiraLinkDirection

class JiraLink(JiraBase):
    def __init__(self, link, jira):
        self.link = link
        if self.direction == JiraLinkDirection.INWARD:
            issue = self.link['inwardIssue']
        elif self.direction == JiraLinkDirection.OUTWARD:
            issue = self.link['outwardIssue']
        super().__init__(issue, jira)

    @cached_property
    def direction(self) -> JiraLinkDirection:
        if 'inwardIssue' in self.link:
            return JiraLinkDirection.INWARD
        elif 'outwardIssue' in self.link:
            return JiraLinkDirection.OUTWARD
        raise NotImplementedError

    @cached_property
    def issue_class(self) -> str:
        if self.is_story:
            return 'JiraStory'
        elif self.is_risk:
            return 'JiraRisk'
        elif self.is_func_requirement:
            return 'JiraFuncRequirement'
        elif self.is_instruction:
            return 'JiraInstruction'
        elif self.is_test:
            return 'JiraTest'
        elif self.is_bug:
            return 'JiraBug'
        return 'JiraIssue'

    @property
    def link_type(self) -> int:
        return int(self.link['type']['id'])

    def is_link(self, link_name: str, direction: JiraLinkDirection) -> bool:
        if direction:
            return self.link_type == self.jira.link_types[link_name]['id'] and self.direction == direction
        return self.link_type == self.jira.link_types[link_name]['id']

    @property
    def is_related(self) -> bool:
        return self.is_link('relates', None)

    @property
    def is_defined_by(self) -> bool:
        return self.is_link('defines', JiraLinkDirection.INWARD)

    @property
    def defines(self) -> bool:
        return self.is_link('defines', JiraLinkDirection.OUTWARD)

    @property
    def is_mitigated_by(self) -> bool:
        return self.is_link('mitigates', JiraLinkDirection.INWARD)

    @property
    def mitigates(self) -> bool:
        return self.is_link('mitigates', JiraLinkDirection.OUTWARD)

    @cached_property
    def full_issue(self):
        return self.jira.get_issue(self.key, self.issue_class)

    def __getattr__(self, name: str):
        return getattr(self.full_issue, name)
