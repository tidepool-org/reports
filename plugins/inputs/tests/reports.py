"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
import os
import logging
import time
from functools import cached_property
from typing import List
import boto3
from botocore import UNSIGNED
from botocore.config import Config

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
        config = Config(
            region_name = self.config['reports']['region'],
            signature_version = UNSIGNED,
            retries = {
                'max_attempts': 10,
                'mode': 'standard'
            }
        )
        self.s3 = boto3.client('s3', config = config)
        self.bucket = self.config['reports']['bucket']
        self.max_keys = 1000

    @cached_property
    def reports(self):
        logger.info('fetching test reports')
        reports = { }
        for key, report in self.latest_files.items():
            reports[key] = self.fetch(key, report)
            logger.info(f'fetched {len(reports[key].test_suites)} test suites and {len(reports[key].test_cases)} test cases from {key}')
        return reports

    def list_bucket(self, contToken):
        if contToken == True: # not truly a continuation token
            response = self.s3.list_objects_v2(Bucket = self.bucket, MaxKeys = self.max_keys)
        else:
            response = self.s3.list_objects_v2(Bucket = self.bucket, MaxKeys = self.max_keys, ContinuationToken = contToken)
        logger.debug(f'list_objects: {response}')
        return ( response['Contents'], response.get('NextContinuationToken') )

    @property
    def latest_files(self):
        files = { }
        contToken = True
        while contToken:
            contents, contToken = self.list_bucket(contToken)
            for content in contents:
                key = content['Key']
                if '.xml' in key:
                    basename = os.path.basename(key)
                    date = content['LastModified']
                    latest = files.get(basename)
                    if latest and latest['date'] > date:
                        continue
                    files[basename] = { 'key': key, 'date': date }
        return files

    def fetch(self, key: str, config: dict):
        logger.info(f"fetching test report {key} from {config}")
        report = self.read_cache(key)
        if report:
            return report
        res = self.s3.get_object(Bucket = self.bucket, Key = config['key'])
        content = res['Body'].read().decode('utf-8')
        self.write_cache(key, content)
        return TestReport(content)

    def read_cache(self, cache_key: str) -> dict:
        if self.cache_ignore:
            return None
        cache_file = os.path.join(self.cache_folder, cache_key)
        if os.path.exists(cache_file):
            if os.stat(cache_file).st_mtime + self.cache_refresh >= time.time():
                logger.debug(f"reading {cache_key} from cache file {cache_file}")
                with open(cache_file, 'r') as f:
                    return TestReport(f.read())
        return None

    def write_cache(self, cache_key: str, content) -> dict:
        cache_file = os.path.join(self.cache_folder, cache_key)
        with open(cache_file, 'w') as f:
            logger.debug(f"writing {cache_key} into cache file {cache_file}")
            f.write(content)
