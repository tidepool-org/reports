from .issue import JiraIssue

class JiraRisk(JiraIssue):
    @property
    def sequence(self):
        return self.format_value('sequence_of_events')

    @property
    def hazard(self):
        return self.format_value('hazard_category')

    @property
    def harm(self):
        return self.format_value('harm')

    @property
    def initial_severity(self):
        return self.format_value('initial_severity')

    @property
    def initial_probability(self):
        return self.format_value('initial_probability')

    @property
    def initial_risk(self):
        return self.format_value('initial_risk')

    @property
    def residual_severity(self):
        return self.format_value('residual_severity')

    @property
    def residual_probability(self):
        return self.format_value('residual_probability')

    @property
    def residual_risk(self):
        return self.format_value('residual_risk')

    @property
    def benefit(self):
        return self.format_value('benefit')

    @property
    def stories(self):
        return [ story for story in self.links if story.inwardType == 'is mitigated by' ]

    def format_value(self, key):
        return self.rendered_fields.get(self.jira.fields[key]) or ''

    def format_weighted_value(self, key):
        val = self.fields.get(self.jira.fields[key])
        if val:
            return f"{val['value']} ({self.jira.get_weight(key, val['id'])})"
        return ''

    def color(self, score: str) -> str:
        score = (score or '').lower()
        if 'green' in score:
            return 'green'
        elif 'yellow' in score:
            return 'yellow'
        elif 'red' in score:
            return 'red'
        return ''
