from functools import cached_property # import functools
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
    def __init__(self, config):
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
        self.queries = self.config['queries']
        self.fields = self.config['fields']
        logger.info("fetching Jira fields")
        self.all_fields = self.jira.get_all_fields()
        logger.debug(f"Jira fields: {json.dumps(self.all_fields, indent=4)}")
        logger.info("fetching Jira custom field schemas")
        self.schemas = {}
        for key, field_id in self.fields.items():
            try:
                custom_key = next(field['key'] for field in self.all_fields if field['id'] == field_id and field['id'] != field['key'])
                # not exposed in Atlassian Jira python API...
                url = f"rest/api/2/field/{custom_key}/option"
                self.schemas[key] = self.jira.get(url)
            except StopIteration:
                pass
            except HTTPError:
                logger.error(f"failed to fetch custom field schema for {custom_key}")
        logger.debug(f"Jira custom field schemas: {json.dumps(self.schemas, indent=4)}")

    def get_weight(self, key, id):
        logger.debug(f"getting weight for {key}, {id}")
        for value in self.schemas[key]['values']:
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

    @cached_property
    def testruns(self):
        logger.info('fetching test runs')
        return self.to_dict(self.jql(self.queries['testruns']), JiraTest)

    @cached_property
    def all_issues(self):
        class AllIssues(dict):
            def __init__(self, jira, *arg, **kw):
                super().__init__(*arg, **kw)
                self.jira = jira

            def __missing__(self, key):
                logger.debug(f'fetching missing issue by key {key}')
                return self.jira.get_issue(key)

        return AllIssues(self, { **self.requirements, **self.risks, **self.epics, **self.stories }) # **self.tests, **self.testruns

    def jql(self, query: str):
        results = [ ]
        start = 0
        while True:
            logger.debug(f"fetching offset {start} of query [{query}]")
            res = self.jira.jql(query, start=start, limit=100, expand="renderedFields")
            results.extend(res['issues'])
            count = int(res['maxResults'])
            logger.debug(f"got {count} results")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(json.dumps(res, indent=4))
            start += count
            if start >= int(res['total']):
                break
        return results

    def get_issue(self, issuekey):
        return JiraIssue(self.jira.get_issue(issuekey), self)

    def to_dict(self, issues, issue_type):
        return { issue.key: issue for issue in [ issue_type(issue, self) for issue in issues ] }

    @staticmethod
    def sorted_by_key(issues):
        def issuekey(issue):
            parts = issue.key.split('-')
            return [ parts[0], int(parts[1]) ]

        # numerical sort of the right side of the issuekey
        # otherwise, LOOP-1234 would sort before LOOP-456
        # this also includes the left side (project key) which is usually same
        # nonetheless, may be useful if we're sorting stories from multiple projects, within an epic
        return sorted(issues, key=issuekey)

    @staticmethod
    def sorted_by_id(issues):
        # numerical sort of the each of the numbers in the id
        # otherwise, 1.2.3 would sort before 1.12.3
        return sorted(issues, key=lambda issue: [ int(id_part) for id_part in issue.id.split('.') ] if issue.id else '' )

    @staticmethod
    def sorted_by_harm(issues):
        return sorted(issues, key=lambda issue: issue.harm)
