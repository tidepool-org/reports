class JiraBase:
    def __init__(self, jira):
        self.jira = jira

    def __eq__(self, other):
        return self.key == other.key

    def __hash__(self):
        return hash(self.key)

    @property
    def type(self):
        pass

    @property
    def key(self):
        return self.issue['key']

    @property
    def url(self):
        return f"{self.jira.config['base_url']}/browse/{self.key}"

    @property
    def icon(self):
        return self.fields['issuetype']['iconUrl']

    @property
    def status(self):
        return self.fields['status']['name']

    @property
    def status_category(self):
        return self.fields['status']['statusCategory']['name']

    @property
    def is_story(self):
        return self.type == 'Story' or self.type == 'Task'

    @property
    def is_test(self):
        return self.type == 'Test'

    @property
    def is_risk(self):
        return self.type == 'Risk Mitigation'

    @property
    def is_junk(self):
        return self.resolution in [ 'Duplicate', "Won't Do" ]

    @property
    def is_done(self):
        return self.status in [ 'Waiting for Approval', 'Waiting for Deployment', 'Closed' ]

    @property
    def is_blocked(self):
        return self.status in [ 'Blocked' ]
