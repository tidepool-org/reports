"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from functools import cached_property # import functools
from typing import List
import os
import time
import logging
import json
import re
import atlassian
from requests.exceptions import HTTPError

import plugins.input

from .issue import JiraIssue
from .epic import JiraEpic
from .story import JiraStory
from .bug import JiraBug
from .test import JiraTest
from .risk import JiraRisk
from .risk_score import JiraRiskScore
from .func_req import JiraFuncRequirement
from .user_req import JiraUserRequirement
from .instruction import JiraInstruction

logger = logging.getLogger(__name__)

class JiraHelper(plugins.input.InputSource):
    _alias_ = 'Jira'
    key = 'jira'

    def __init__(self, config: dict):
        super().__init__(config)
        if 'base_url' not in self.config:
            self.config['base_url'] = os.environ.get('JIRA_BASE_URL')
        if 'username' not in self.config:
            self.config['username'] = os.environ.get('JIRA_USERNAME')
        if 'api_token' not in self.config:
            self.config['api_token'] = os.environ.get('JIRA_API_TOKEN')
        logger.info(f"connecting to Jira as '{self.config['username']}'")
        self.jira = atlassian.Jira(
            url = self.config['base_url'],
            username = self.config['username'],
            password = self.config['api_token'])
        self.cache_folder = self.config['cache']['folder']
        self.cache_ignore = self.config['refresh_cache']
        os.makedirs(self.cache_folder, exist_ok = True)
        self.cache_refresh = int(self.config['cache']['refresh'])
        self.parameters = self.config['parameters']
        self.queries = self.config['queries']
        self.fields = self.config['fields']
        self.issue_types = self.config['issue_types']
        self.link_types = self.config['link_types']
        self.junk_resolution = self.config['filters']['junk_resolution']
        self.done_status = self.config['filters']['done_status']
        self.blocked_status = self.config['filters']['blocked_status']
        self.field_list = [ '*all', *[ f'-{field}' for field in self.config['exclude_fields'] ] ]
        logger.debug(f"requesting fields: {', '.join(self.field_list)}")
        self.missed = { }
        self.all_fields
        self.all_schemas
        self.all_link_types

    @property
    def risk_scores(self):
        return { JiraRiskScore.GREEN: 0, JiraRiskScore.YELLOW: 0, JiraRiskScore.RED: 0, JiraRiskScore.UNKNOWN: 0 }

    @cached_property
    def all_issues(self):
        return { **self.func_requirements, **self.user_requirements, **self.risks, **self.stories, **self.bugs, **self.epics, **self.tests, **self.instructions }

    @cached_property
    def all_fields(self):
        fields = self.read_cache('fields')
        if fields:
            return fields
        logger.info("fetching Jira fields")
        fields = self.jira.get_all_fields()
        logger.debug(f"Jira fields: {json.dumps(fields, indent = 4)}")
        self.write_cache('fields', fields)
        return fields

    @cached_property
    def all_schemas(self):
        schemas = self.read_cache('schemas')
        if schemas:
            return schemas
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
        logger.debug(f"Jira custom field schemas: {json.dumps(schemas, indent = 4)}")
        self.write_cache('schemas', schemas)
        return schemas

    @cached_property
    def all_link_types(self):
        link_types = self.read_cache('link_types')
        if link_types:
            return link_types
        logger.info("fetching Jira link types")
        link_types = self.jira.get_issue_link_types()
        logger.debug(f"Jira link types: {json.dumps(link_types, indent = 4)}")
        self.write_cache('link_types', link_types)
        return link_types

    def get_weight(self, key: str, id: str):
        logger.debug(f"getting weight for {key}, {id}")
        for value in self.all_schemas[key]['values']:
            if value['id'] == id:
                return value['properties']['weight']
        return None

    @cached_property
    def func_requirements(self):
        logger.info('fetching functional requirements')
        return self.to_dict(self.jql('func_requirements'), JiraFuncRequirement)

    @cached_property
    def user_requirements(self):
        logger.info('fetching user requirements')
        return self.to_dict(self.jql('user_requirements'), JiraUserRequirement)

    @cached_property
    def risks(self):
        logger.info('fetching risks')
        return self.to_dict(self.jql('risks'), JiraRisk)

    @cached_property
    def epics(self):
        logger.info('fetching epics')
        return self.to_dict(self.jql('epics'), JiraEpic)

    @cached_property
    def stories(self):
        logger.info('fetching stories')
        return self.to_dict(self.jql('stories'), JiraStory)

    @cached_property
    def bugs(self):
        logger.info('fetching bugs')
        return self.to_dict(self.jql('bugs'), JiraBug)

    @cached_property
    def tests(self):
        logger.info('fetching tests')
        return self.to_dict(self.jql('tests'), JiraTest)

    @cached_property
    def instructions(self):
        logger.info('fetching instructions')
        return self.to_dict(self.jql('instructions'), JiraInstruction)

    def jql(self, query: str):
        results = self.read_cache(query)
        if results:
            return results
        jql = self.queries[query].format(**self.parameters)
        results = [ ]
        start = 0
        while True:
            logger.debug(f"fetching offset {start} of query {query} = [{jql}]")
            res = self.jira.jql(jql, start = start, limit = 100, fields = self.field_list, expand = "renderedFields")
            results.extend(res['issues'])
            count = int(res['maxResults'])
            total = int(res['total'])
            logger.debug(f"got {count} results out of {total}")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(json.dumps(res, indent = 4))
            start += count
            if start >= total:
                break
        self.write_cache(query, results)
        return results

    def __get_issue(self, issue_key: str, cls = JiraIssue):
        issue = self.read_cache(issue_key)
        if not issue:
            issue = self.jira.get_issue(issue_key, fields = self.field_list)
            logger.debug(f'got issue {cls.__name__} {issue_key}: {json.dumps(issue, indent = 4)}')
            self.write_cache(issue_key, issue)
        return cls(issue, self)

    def get_issue(self, issue_key: str, cls = JiraIssue):
        if isinstance(cls, str):
            cls = globals()[cls]
        logger.debug(f'requesting {cls.__name__} {issue_key}')
        issue = self.all_issues.get(issue_key)
        if not issue:
            issue = self.missed.get(issue_key)
            if not issue:
                logger.debug(f'cache miss, fetching {cls.__name__} {issue_key}')
                issue = self.__get_issue(issue_key, cls)
                self.missed[issue_key] = issue
        return issue

    def to_dict(self, issues: List[JiraIssue], issue_type: str) -> dict:
        return { issue.key: issue for issue in [ issue_type(issue, self) for issue in issues ] }

    def read_cache(self, cache_key: str) -> dict:
        if self.cache_ignore:
            return None
        cache_file = os.path.join(self.cache_folder, f"{cache_key}.json")
        if os.path.exists(cache_file):
            if os.stat(cache_file).st_mtime + self.cache_refresh >= time.time():
                logger.debug(f"reading {cache_key} from cache file {cache_file}")
                with open(cache_file, 'r') as f:
                    return json.load(f)
        return None

    def write_cache(self, cache_key: str, content) -> dict:
        cache_file = os.path.join(self.cache_folder, f"{cache_key}.json")
        with open(cache_file, 'w') as f:
            logger.debug(f"writing {cache_key} into cache file {cache_file}")
            json.dump(content, f, indent = 4)

    @staticmethod
    def prettify_links(text: str) -> str:
        text = re.sub(r"""(<a.+>)(?:https://docs.google.+)(</a>)""", r"""\1Google Document\2""", text)
        text = re.sub(r"""\[(https://docs.google.+)\|([^]]+)\]""", r"""<a href="\1">Google Document</a>""", text)
        return re.sub(r"""(<a.+>)(?:https://tidepool.atlassian.net/browse/)(\w+-\d+)(</a>)""", r"""\1\2\3""", text)

    @staticmethod
    def exclude_junk(issues: List[JiraIssue], enforce_versions: bool = False) -> List[JiraIssue]:
        if enforce_versions:
            return [ issue for issue in issues if not issue.is_junk and issue.jira.parameters['fix_version'] in issue.full_issue.fix_versions ]
        return [ issue for issue in issues if not issue.is_junk ]

    @staticmethod
    def filter_by(issues: List[JiraIssue], filter: List[str]) -> List[JiraIssue]:
        return [ issue for issue in issues if issue.key in filter ]

    @staticmethod
    def sorted_by_key(issues: List[JiraIssue]) -> List[JiraIssue]:
        def issuekey(issue):
            parts = issue.key.split('-')
            return [ parts[0], int(parts[1]) ]

        # numerical sort of the right side of the issuekey
        # otherwise, LOOP-1234 would sort before LOOP-456
        # this also includes the left side (project key) which is usually same
        # nonetheless, may be useful if we're sorting stories from multiple projects, within an epic
        return sorted(issues, key = issuekey)

    @staticmethod
    def sorted_by_id(issues: List[JiraIssue]) -> List[JiraIssue]:
        # numerical sort of the each of the numbers in the id
        # otherwise, 1.2.3 would sort before 1.12.3
        return sorted(issues, key = lambda issue: [ int(id_part) for id_part in issue.id.split('.') ] if issue.id else [ 0 ] )

    @staticmethod
    def sorted_by_harm(issues: List[JiraIssue]) -> List[JiraIssue]:
        return sorted(issues, key = lambda issue: f'{issue.harm}:{issue.hazard_category}')

    @staticmethod
    def sorted_by_fix_version(issues: List[JiraIssue]) -> List[JiraIssue]:
        return sorted(issues, key = lambda issue: f'{",".join(sorted(issue.fix_versions))}:{issue.status}:{issue.key}')
