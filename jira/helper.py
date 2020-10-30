from functools import cached_property # import functools
from typing import List
import os
import logging
import json
import re
import atlassian
from requests.exceptions import HTTPError

from .issue import JiraIssue
from .epic import JiraEpic
from .story import JiraStory
from .test import JiraTest
from .risk import JiraRisk
from .requirement import JiraRequirement

logger = logging.getLogger(__name__)

class JiraHelper():
    def __init__(self, config: dict):
        self.config = config
        if 'base_url' not in self.config:
            self.config['base_url'] = os.environ.get('JIRA_BASE_URL')
        if 'username' not in self.config:
            self.config['username'] = os.environ.get('JIRA_USERNAME')
        if 'api_token' not in self.config:
            self.config['api_token'] = os.environ.get('JIRA_API_TOKEN')
        logger.info(f"connecting to Jira as '{self.config['username']}'")
        self.jira = atlassian.Jira(
            url=self.config['base_url'],
            username=self.config['username'],
            password=self.config['api_token'])
        self.parameters = self.config['parameters']
        self.queries = self.config['queries']
        self.fields = self.config['fields']
        self.field_list = [ '*all', '-project', '-comment', '-attachment', '-creator', '-reporter', '-assignee', '-watches', '-votes', '-worklog', '-customfield_10073' ]
        self.missed = { }

    @cached_property
    def all_issues(self):
        return { **self.requirements, **self.risks, **self.stories, **self.epics }

    @cached_property
    def all_fields(self):
        logger.info("fetching Jira fields")
        fields = self.jira.get_all_fields()
        logger.debug(f"Jira fields: {json.dumps(fields, indent=4)}")
        return fields

    @cached_property
    def all_schemas(self):
        logger.info("fetching Jira custom field schemas")
        schemas = {}
        for key, field_id in self.fields.items():
            try:
                custom_key = next(field['key'] for field in self.all_fields if field['id'] == field_id and field['id'] != field['key'] and field['schema']['type'] != 'string')
                # not exposed in Atlassian Jira python API...
                url = f"rest/api/2/field/{custom_key}/option"
                schemas[key] = self.jira.get(url)
            except StopIteration:
                pass
            except HTTPError as err:
                logger.warn(f"failed to fetch custom field schema for {custom_key}, reason {err.response.status_code}")
        logger.debug(f"Jira custom field schemas: {json.dumps(schemas, indent=4)}")
        return schemas

    def get_weight(self, key: str, id: str):
        logger.debug(f"getting weight for {key}, {id}")
        for value in self.all_schemas[key]['values']:
            if value['id'] == id:
                return value['properties']['weight']
        return None

    @cached_property
    def requirements(self):
        logger.info('fetching requirements')
        return self.to_dict(self.jql(self.queries['requirements']), JiraRequirement)

    @cached_property
    def risks(self):
        logger.info('fetching risks')
        return self.to_dict(self.jql(self.queries['risks']), JiraRisk)

    @cached_property
    def epics(self):
        logger.info('fetching epics')
        return self.to_dict(self.jql(self.queries['epics']), JiraEpic)

    @cached_property
    def stories(self):
        logger.info('fetching stories')
        return self.to_dict(self.jql(self.queries['stories']), JiraStory)

    @cached_property
    def tests(self):
        logger.info('fetching tests')
        return self.to_dict(self.jql(self.queries['tests']), JiraTest)

    def jql(self, query: str):
        query = query.format(**self.parameters)
        results = [ ]
        start = 0
        while True:
            logger.debug(f"fetching offset {start} of query [{query}]")
            res = self.jira.jql(query, start=start, limit=100, fields=self.field_list, expand="renderedFields")
            results.extend(res['issues'])
            count = int(res['maxResults'])
            total = int(res['total'])
            logger.debug(f"got {count} results out of {total}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(json.dumps(res, indent=4))
            start += count
            if start >= total:
                break
        return results

    def __get_issue(self, issue_key: str, cls=JiraIssue):
        issue = self.jira.get_issue(issue_key, fields=self.field_list)
        logger.debug(f'got issue {issue_key} of type {cls}: {json.dumps(issue, indent=4)}')
        return cls(issue, self)

    def get_issue(self, issue_key: str, cls=JiraIssue):
        logger.debug(f"requesting {issue_key} of type {cls}")
        if isinstance(cls, str):
            cls = globals()[cls]
        issue = self.all_issues.get(issue_key)
        if not issue:
            issue = self.missed.get(issue_key)
            if not issue:
                logger.debug(f"cache miss, fetching {issue_key} of type {cls}")
                issue = self.__get_issue(issue_key, cls)
                self.missed[issue_key] = issue
        return issue

    def to_dict(self, issues: List[JiraIssue], issue_type: str) -> dict:
        return { issue.key: issue for issue in [ issue_type(issue, self) for issue in issues ] }

    @staticmethod
    def prettify_links(text: str) -> str:
        text = re.sub(r"""(<a.+>)(?:https://docs.google.+)(</a>)""", r"""\1Google Document\2""", text)
        return re.sub(r"""(<a.+>)(?:https://tidepool.atlassian.net/browse/)(\w+-\d+)(</a>)""", r"""\1\2\3""", text)

    @staticmethod
    def exclude_junk(issues: List[JiraIssue], enforce_versions: bool = False) -> List[JiraIssue]:
        if enforce_versions:
            return [ issue for issue in issues if not issue.is_junk and issue.jira.parameters['fix_version'] in issue.fix_versions ]
        return [ issue for issue in issues if not issue.is_junk ]

    @staticmethod
    def sorted_by_key(issues: List[JiraIssue]) -> List[JiraIssue]:
        def issuekey(issue):
            parts = issue.key.split('-')
            return [ parts[0], int(parts[1]) ]

        # numerical sort of the right side of the issuekey
        # otherwise, LOOP-1234 would sort before LOOP-456
        # this also includes the left side (project key) which is usually same
        # nonetheless, may be useful if we're sorting stories from multiple projects, within an epic
        return sorted(issues, key=issuekey)

    @staticmethod
    def sorted_by_id(issues: List[JiraIssue]) -> List[JiraIssue]:
        # numerical sort of the each of the numbers in the id
        # otherwise, 1.2.3 would sort before 1.12.3
        return sorted(issues, key=lambda issue: [ int(id_part) for id_part in issue.id.split('.') ] if issue.id else [ 0 ] )

    @staticmethod
    def sorted_by_harm(issues: List[JiraIssue]) -> List[JiraIssue]:
        return sorted(issues, key=lambda issue: issue.harm)
