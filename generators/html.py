import os
import logging
import shutil
import re
import markdown
import jinja2
from typing import List

logger = logging.getLogger(__name__)

class Html():
    def __init__(self, jira, config: dict):
        self.jira = jira
        self.config = config

    def generate(self) -> List[str]:
        files = [ ]
        for image_key, source_file in self.config['images'].items():
            target_file = self.config['output'][image_key]
            logger.info(f"copying {target_file} from {source_file}")
            self.copy(source_file, target_file)
            files.append(target_file)

        for template_key, source_file in self.config['templates'].items():
            env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(os.path.dirname(source_file)),
                autoescape=jinja2.select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True,
                # enable_async=True,
            )
            env.filters['exclude_junk'] = self.jira.exclude_junk
            env.filters['sort_by_key'] = self.jira.sorted_by_key
            env.filters['sort_by_id'] = self.jira.sorted_by_id
            env.filters['sort_by_harm'] = self.jira.sorted_by_harm
            env.filters['prettify_links'] = lambda text: re.sub(r"""(<a.+>)(?:https://docs.google.+)(</a>)""", r"""\1Google Doc\2""", text)
            md = markdown.Markdown()
            env.filters['markdown'] = lambda text: jinja2.Markup(md.convert(text))

            target_file = self.config['output'][template_key]
            logger.info(f"generating {target_file} from {source_file}")
            template = env.get_template(os.path.basename(source_file))
            os.makedirs(os.path.dirname(target_file), exist_ok=True)
            with open(target_file, 'w') as file:
                file.write(template.render(now=self.config['generated'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z'), jira=self.jira, config=self.config, basename=lambda name: os.path.basename(name)))
            files.append(target_file)
        return files

    def copy(self, source_file: str, target_file: str):
        os.makedirs(os.path.dirname(target_file), exist_ok=True)
        shutil.copy(source_file, target_file)
