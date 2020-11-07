from typing import List
from functools import cached_property
import pluginlib

@pluginlib.Parent('output')
class OutputGenerator():
    key = pluginlib.abstractattribute
    flag = pluginlib.abstractattribute
    description = pluginlib.abstractattribute

    def __init__(self, config: dict, inputs: dict):
        self.config = config
        self.inputs = inputs

    @cached_property
    def jira(self):
        return self.inputs['jira']

    @cached_property
    def test_reports(self):
        return self.inputs['tests']

    @pluginlib.abstractmethod
    def generate(self) -> List[str]:
        pass
