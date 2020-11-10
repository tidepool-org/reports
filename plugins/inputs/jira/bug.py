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
        return self.fields[self.jira.fields['risk_level']]

    @property
    def uea_level(self):
        return self.fields[self.jira.fields['uea_level']]
