class TestSuite():
    def __init__(self, suite):
        self.name = suite.get('name')
        self.tests = int(suite.get('tests') or 0)
        self.failures = int(suite.get('failures') or 0)
        self.errors = int(suite.get('errors') or 0)
        self.skipped = int(suite.get('skipped') or 0)
        self.time = float(suite.get('time') or 0)
