"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
import logging
from typing import List

from .issue import JiraIssue
from .risk_score import JiraRiskScore

logger = logging.getLogger(__name__)

class JiraRisk(JiraIssue):
    @property
    def source(self):
        return self.fields.get(self.jira.fields['source']) or ''

    @property
    def sequence(self):
        return self.format_value('sequence_of_events')

    @property
    def hazard(self):
        return self.fields.get(self.jira.fields['hazard']) or ''

    @property
    def hazard_category(self):
        return self.format_value('hazard_category')

    @property
    def harm(self):
        return self.fields.get(self.jira.fields['harm']) or ''

    @property
    def initial_severity(self):
        return self.format_value('initial_severity')

    @property
    def initial_probability(self):
        return self.format_value('initial_probability')

    @property
    def initial_risk(self):
        return self.format_value('initial_risk')

    @property
    def residual_severity(self):
        return self.format_value('residual_severity')

    @property
    def residual_probability(self):
        return self.format_value('residual_probability')

    @property
    def residual_risk(self):
        return self.format_value('residual_risk')

    @property
    def benefit(self):
        return self.format_value('benefit')

    @property
    def stories(self):
        return [ self.jira.get_issue(link.key, link.issue_class) for link in self.links if link.is_story ]

    def format_value(self, key):
        return self.rendered_fields.get(self.jira.fields[key]) or ''

    def format_weighted_value(self, key):
        val = self.fields.get(self.jira.fields[key])
        if val:
            return f"{val['value']} ({self.jira.get_weight(key, val['id'])})"
        return ''

    def score(self, score: str, state: str) -> JiraRiskScore:
        if score is None or score == '':
            logger.warn(f"{self.key} {self.fix_versions} {self.status}: {state} risk score is not set")
            return JiraRiskScore.UNKNOWN
        normalized_score = (score or '').lower()
        if 'green' in normalized_score:
            return JiraRiskScore.GREEN
        elif 'yellow' in normalized_score:
            return JiraRiskScore.YELLOW
        elif 'red' in normalized_score:
            return JiraRiskScore.RED
        logger.warn(f"{self.key} {self.fix_versions} {self.status}: {state} risk score '{score}' (normalized as '{normalized_score}') does not match a known score")
        return JiraRiskScore.UNKNOWN

    def color(self, score: str, state: str) -> str:
        score = self.score(score, state)
        if score == JiraRiskScore.GREEN:
            return 'green'
        elif score == JiraRiskScore.YELLOW:
            return 'yellow'
        elif score == JiraRiskScore.RED:
            return 'red'
        return ''

    @property
    def mitigations(self) -> List[JiraIssue]:
        mitigations = set() # only list unique mitigations
        logger.debug(f'examining {self.key} links: {",".join([ link.key for link in self.links ])}')
        for issue in self.jira.exclude_junk(self.links, enforce_versions = False):
            logger.debug(f'looking at {issue.type} {issue.key} {issue.url}')
            if issue.is_func_requirement: # if it's a TLFR, use it directly
                logger.debug(f'showing issue {issue.key} directly, it is a functional requirement')
                mitigations.add(issue)
            elif (issue.is_story and issue.is_mitigated_by) or issue.is_instruction:
                if len(issue.defined_by) == 0: # has no functional requirements
                    logger.debug(f'showing issue {issue.key} directly, no new functional requirements were found')
                    mitigations.add(issue)
                else:
                    for func_req in issue.defined_by:
                        logger.debug(f'showing functional requirement {func_req.key} instead of {issue.key}')
                        logger.debug(f'--> added {func_req.type} {func_req.key} {func_req.url}')
                        mitigations.add(func_req)
            elif issue.is_story or issue.is_instruction:
                logger.debug(f'showing issue {issue.key} directly')
                mitigations.add(issue)
            else:
                logger.debug(f'skipping issue {issue.key} because it is not a story or instruction')
        return list(mitigations)
