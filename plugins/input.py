"""
Base for all input source plug-ins

Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
import pluginlib

@pluginlib.Parent('input')
class InputSource():
    """
    Base class for all input source plug-ins
    """
    key = pluginlib.abstractattribute

    def __init__(self, config: dict):
        self.config = config
