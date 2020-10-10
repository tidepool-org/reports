import logging
import re
from graphviz import Digraph
import html

logger = logging.getLogger(__name__)

class GraphViz():
    def __init__(self, jira, config):
        self.jira = jira
        self.config = config

    def generate(self) -> None:
        self.graph_by_requirements()
        self.graph_by_epics()

    def graph_by_requirements(self) -> None:
        output = self.config['output']['requirements']
        graph_file = output['graph']
        logger.info(f"generating {graph_file}")
        graph = Digraph(comment=f"Generated on {self.config['generated']}", graph_attr={'rankdir': 'LR', 'splines': 'ortho'}, node_attr={'shape': 'none'})

        for req in self.jira.sorted_by_id(self.jira.requirements.values()):
            self.add_node(graph, req)

            for risk in self.jira.sorted_by_key(req.risks):
                self.add_node(graph, risk)
                self.add_edge(graph, req, risk)

            for story in self.jira.sorted_by_key(req.stories):
                self.add_node(graph, story)
                self.add_edge(graph, req, story)
                for test in self.jira.sorted_by_key(story.tests):
                    self.add_node(graph, test)
                    self.add_edge(graph, story, test)

        graph.engine = output['engine']
        graph.format = output['format']
        graph.render(filename=graph_file, cleanup=False, view=False)

    def graph_by_epics(self) -> None:
        output = self.config['output']['epics']
        graph_file = output['graph']
        logger.info(f"generating {graph_file}")
        graph = Digraph(comment=f"Generated on {self.config['generated']}", graph_attr={'rankdir': 'LR', 'splines': 'ortho'}, node_attr={'shape': 'none'})

        for epic in self.jira.sorted_by_key(self.jira.epics.values()):
            self.add_node(graph, epic)

            for story in self.jira.sorted_by_key(epic.stories):
                self.add_node(graph, story)
                self.add_edge(graph, epic, story)
                for risk in self.jira.sorted_by_key(story.risks):
                    self.add_node(graph, risk)
                    self.add_edge(graph, story, risk)
                for test in self.jira.sorted_by_key(story.tests):
                    self.add_node(graph, test)
                    self.add_edge(graph, story, test)

        graph.engine = output['engine']
        graph.format = output['format']
        graph.render(filename=graph_file, cleanup=False, view=False)

    @staticmethod
    def node_id(issue) -> str:
        return re.sub('-', '_', issue.key)

    def add_node(self, graph, issue) -> None:
        graph.node(self.node_id(issue), f"""<
            <table border="0" cellborder="1" cellspacing="0" cellpadding="4" style="rounded">
                <tr>
                    <td align="left" port="key"><b>{issue.key}</b></td>
                </tr>
                <tr>
                    <td>{html.escape(issue.summary)}</td>
                </tr>
            </table>
        >""")

    def add_edge(self, graph, from_issue, to_issue) -> None:
        graph.edge(f'{self.node_id(from_issue)}:key:e', f'{self.node_id(to_issue)}:key:w')
