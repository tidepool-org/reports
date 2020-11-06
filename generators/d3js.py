import os
import logging
import shutil
import jinja2
import json
from functools import cached_property
from typing import List

logger = logging.getLogger(__name__)

class Node(dict):
    def __init__(self, name: str, summary: str = ''):
        self['name'] = name
        self['summary'] = summary
        self['children'] = [ ]

    def add_child(self, child):
        node = Node(child.key, child.summary)
        self['children'].append(node)
        return node


class D3js():
    def __init__(self, jira, config):
        self.jira = jira
        self.config = config

    def generate(self) -> List[str]:
        files = [ ]

        for graph, config in self.config['graphs'].items():
            logger.info(f"generating D3.js visualization output {graph}")
            for image_key, source_file in config.get('images', { }).items():
                target_file = config['output'][image_key]
                logger.info(f"copying {target_file} from {source_file}")
                self.copy(source_file, target_file)
                files.append(target_file)

            for template_key, source_file in config.get('templates', { }).items():
                target_file = config['output'].get(template_key)
                if not target_file:
                    logger.info(f"skipping template {template_key} {source_file}, no target file")
                    continue
                env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(os.path.dirname(source_file)),
                    autoescape=jinja2.select_autoescape(['html', 'xml']),
                    trim_blocks=True,
                    lstrip_blocks=True,
                    # enable_async=True,
                )

                logger.info(f"generating {target_file} from {source_file}")
                template = env.get_template(os.path.basename(source_file))
                os.makedirs(os.path.dirname(target_file), exist_ok=True)
                with open(target_file, 'w') as file:
                    file.write(template.render(now=self.config['generated'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z'), jira=self.jira, nodes=self.nodes, config=self.config, basename=lambda name: os.path.basename(name)))
                files.append(target_file)

            logger.info(f"done generating D3.js visualization output {graph}")

        return files

    def copy(self, source_file: str, target_file: str):
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        shutil.copy(source_file, target_file)

    @cached_property
    def nodes(self):
        root_node = Node('Tidepool Loop v1.0')
        for req in self.jira.sorted_by_id(self.jira.exclude_junk(self.jira.func_requirements.values(), enforce_versions = False)):
            req_node = root_node.add_child(req)
            for risk in self.jira.sorted_by_key(self.jira.exclude_junk(req.risks, enforce_versions = False)):
                risk_node = req_node.add_child(risk)
                # for mitigation in self.jira.sorted_by_key(self.jira.exclude_junk(risk.mitigations, enforce_versions = False)):
                #     risk_node.add_child(mitigation.key)

            for story in self.jira.sorted_by_key(self.jira.exclude_junk(req.stories, enforce_versions = True)):
                story_node = req_node.add_child(story)
                for test in self.jira.sorted_by_key(self.jira.exclude_junk(story.tests, enforce_versions = False)):
                    story_node.add_child(test)

        return json.dumps(root_node, indent = 4)
