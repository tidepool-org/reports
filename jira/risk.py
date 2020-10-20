from .issue import JiraIssue

class JiraRisk(JiraIssue):
    @property
    def sequence(self):
        return self.rendered_fields[self.jira.fields['sequence_of_events']] or ''

    @property
    def hazard(self):
        return self.fields[self.jira.fields['hazard_category']] or ''

    @property
    def harm(self):
        return self.fields[self.jira.fields['harm']] or ''

    def format_value(self, key):
        val = self.fields[self.jira.fields[key]]
        if val:
            return f"{val['value']} ({self.jira.get_weight(key, val['id'])})"
        return ''

    @property
    def initial_severity(self):
        return self.format_value('initial_severity')

    @property
    def initial_probability(self):
        return self.format_value('initial_probability')

    @property
    def initial_risk(self):
        return self.rendered_fields[self.jira.fields['initial_risk']] or ''

    @property
    def residual_severity(self):
        return self.format_value('residual_severity')

    @property
    def residual_probability(self):
        return self.format_value('residual_probability')

    @property
    def residual_risk(self):
        return self.rendered_fields[self.jira.fields['residual_risk']] or ''

    @property
    def benefit(self):
        return self.rendered_fields[self.jira.fields['benefit']] or ''

    @property
    def stories(self):
        return [ story for story in self.links if story.inwardType == 'is mitigated by' ]
