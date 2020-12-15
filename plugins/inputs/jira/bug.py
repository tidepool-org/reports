"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
import logging
from .story import JiraStory

logger = logging.getLogger(__name__)

class JiraBug(JiraStory):
    @property
    def risk_level(self):
        level = self.fields[self.jira.fields['risk_level']]
        if level:
            return int(level.get('value', '0'))
        return ''

    @property
    def uea_level(self):
        level = self.fields[self.jira.fields['uea_level']]
        if level:
            return int(level.get('value', '0'))
        return ''
