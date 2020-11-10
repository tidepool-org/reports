"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
import os
import logging
import time
import requests
from functools import cached_property
from typing import List

import plugins.input
from .report import TestReport

logger = logging.getLogger(__name__)

class TestReports(plugins.input.InputSource):
    _alias_ = 'Test Reports'
    key = 'tests'

    def __init__(self, config):
        super().__init__(config)
        self.cache_folder = self.config['cache']['folder']
        self.cache_ignore = self.config['refresh_cache']
        os.makedirs(self.cache_folder, exist_ok = True)
        self.cache_refresh = int(self.config['cache']['refresh'])

    @cached_property
    def reports(self):
        logger.info('fetching test reports')
        reports = { }
        for key, report in self.config['reports'].items():
            reports[key] = self.fetch(key, report)
            logger.info(f'fetched {len(reports[key].test_suites)} test suites and {len(reports[key].test_cases)} test cases')
        return reports

    def fetch(self, key: str, config: dict):
        logger.info(f"fetching test report {key} from {config['url']}")
        report = self.read_cache(key)
        if report:
            return report
        if 'https:' in config['url']:
            res = requests.get(config['url'])
            if res.text:
                self.write_cache(key, res.text)
                return TestReport(res.text)
        else:
            with open(config['url'], 'r') as f:
                return TestReport(f.read())
        return None

    def read_cache(self, cache_key: str) -> dict:
        if self.cache_ignore:
            return None
        cache_file = os.path.join(self.cache_folder, f"{cache_key}.xml")
        if os.path.exists(cache_file):
            if os.stat(cache_file).st_mtime + self.cache_refresh >= time.time():
                logger.debug(f"reading {cache_key} from cache file {cache_file}")
                with open(cache_file, 'r') as f:
                    return TestReport(f.read())
        return None

    def write_cache(self, cache_key: str, content) -> dict:
        cache_file = os.path.join(self.cache_folder, f"{cache_key}.xml")
        with open(cache_file, 'w') as f:
            logger.debug(f"writing {cache_key} into cache file {cache_file}")
            f.write(content)
