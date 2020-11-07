from typing import List
import logging
import pdfkit

import plugins.output

logger = logging.getLogger(__name__)

class Pdf(plugins.output.OutputGenerator):
    key = 'pdf'
    flag = '--pdf'
    description = 'generate PDF output from HTML'
    _alias_ = 'PDF'

    def __init__(self, jira, config):
        self.jira = jira
        self.config = config

    def generate(self) -> List[str]:
        source_file = self.config['input']['report']
        target_file = self.config['output']['report']
        cover_file = self.config['input']['cover']
        header_file = self.config['input']['header']
        logger.info(f"generating {target_file} from {source_file} with {cover_file} and {header_file}")
        options = {
            'enable-local-file-access': None,
            'encoding': 'UTF-8',
            'print-media-type': None,
            'page-size': 'Legal',
            'orientation': 'Landscape',
            'margin-top': '0.5in',
            'margin-right': '0.5in',
            'margin-bottom': '0.5in',
            'margin-left': '0.5in',
            'header-line': None,
            'header-spacing': 5,
            'header-font-name': 'Helvetica Neue',
            'header-font-size': 10,
            'header-html': header_file,
            'footer-line': None,
            'footer-font-name': 'Helvetica Neue',
            'footer-font-size': 10,
            'footer-left': 'Tidepool Loop 1.0 Verification Report',
            'footer-center': f"Generated on {self.config['generated']}",
            'footer-right': 'Page [frompage] of [topage]'
        }
        pdfkit.from_file(source_file, target_file, options = options, cover = cover_file)
