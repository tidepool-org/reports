import logging

from .issue import JiraIssue

logger = logging.getLogger(__name__)

class JiraFuncRequirement(JiraIssue):
    @property
    def id(self):
        return self.fields[self.jira.fields['reference_id']] or ''

    @property
    def risks(self):
        all = set(super().risks)
        logger.debug(f'direct risks attached to {self.key}: {len(all)}')
        # aggregate indirect risks from linked stories
        for story in self.stories:
            indirect_risks = self.jira.get_issue(story.key, JiraIssue).risks
            logger.debug(f'indirect risks through {story.key}: {len(indirect_risks)}')
            all.update(indirect_risks)
        return all
