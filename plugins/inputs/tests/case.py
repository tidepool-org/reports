"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
class TestCase():
    def __init__(self, test):
        self.suite = test.get('classname')
        self.name = test.get('name')
        self.time = float(test.get('time'))
        self.status = True
