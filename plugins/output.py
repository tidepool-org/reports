"""
Base for all output generator plug-ins

Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from typing import List
from functools import cached_property
import pluginlib

@pluginlib.Parent('output')
class OutputGenerator():
    """
    Base class for all output generator plug-ins
    """
    key = pluginlib.abstractattribute
    flag = pluginlib.abstractattribute
    description = pluginlib.abstractattribute

    def __init__(self, config: dict, inputs: dict):
        self.config = config
        self.inputs = inputs

    @cached_property
    def jira(self):
        """
        Returns reference to the Jira input source
        """
        return self.inputs['jira']

    @cached_property
    def test_reports(self):
        """
        Returns reference to the test reports input source
        """
        return self.inputs['tests']

    @pluginlib.abstractmethod
    def generate(self) -> List[str]:
        """
        Render the output file(s) provided by this generator
        """
        # pass
