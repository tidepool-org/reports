import logging
from typing import Tuple, List, NamedTuple, Optional
from functools import cached_property
import re
import xlsxwriter
from enum import IntEnum
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

def log_issue(issue, indent: int = 0):
    logger.debug(f"{indent * '--> '}added {issue.type} {issue.key} {issue.url}")

GREEN_CHECKMARK = '\u2705'
RED_X = '\u274C'

PASSED = f'{GREEN_CHECKMARK} PASSED '
BLOCKED = f'{RED_X} BLOCKED '

class BaseSegment():
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True

    @property
    def is_closed(self):
        return self.closed

    @property
    def is_empty(self):
        pass

class Text(BaseSegment):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def append(self, text):
        self.text += text

    @property
    def is_empty(self):
        return len(self.text) == 0

    @property
    def rendered(self):
        return self.text

class HyperLink(BaseSegment):
    def __init__(self, url, text = None):
        super().__init__()
        self.url = url
        self.text = text

    def append(self, text):
        self.text = text

    @property
    def pretty_link(self):
        if self.text.startswith('https://docs.google'):
            return 'Google Document'
        return self.text

    @property
    def is_empty(self):
        return False

    @property
    def rendered(self):
        return self.pretty_link

class HtmlToExcel(HTMLParser):
    def __init__(self, bold_format):
        super().__init__()
        self.nodes = [ ]
        self.bold_format = bold_format

    def parse(self, text):
        self.reset()
        self.feed(text)
        self.close()
        return self

    @property
    def is_empty(self):
        return len(self.nodes) == 0

    @property
    def last_node(self):
        return self.nodes[-1]

    def add_node(self, node):
        self.nodes.append(node)

    def append_to_last(self, text):
        self.last_node.append(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = next(attr[1] for attr in attrs if attr[0] == 'href')
            self.add_node(HyperLink(href))

    def handle_endtag(self, tag):
        self.last_node.close()

    def handle_data(self, data):
        stripped = ' '.join(data.split())
        if len(stripped) > 0:
            if self.is_empty or self.last_node.is_closed:
                self.add_node(Text(stripped))
            else:
                self.append_to_last(stripped)

    @cached_property
    def rendered(self):
        return '\n'.join(seg.rendered for seg in self.nodes if not seg.is_empty)

class Column(NamedTuple):
    column: int
    width: int
    row: int
    key: str
    label: str

    def __int__(self) -> int:
        return self.column

class Columns(dict):
    def __init__(self, columns: List[dict], row: int = 0):
        for i, column in enumerate(columns):
            col = Column(row=row, column=i, **column)
            self[col.column] = col
            self[col.key] = col
        self.row = row

    @property
    def ordered(self):
        return sorted([ column for key, column in self.items() if isinstance(key, int) ], key=lambda col: col.column)

    def __len__(self):
        return len(self.ordered)

    @property
    def first(self):
        return 0

    @property
    def last(self):
        return len(self) - 1

    def find_all(self, *names: List[str]) -> List[Column]:
        return [ column for key, column in self.items() if isinstance(key, str) and column.key in names ]

class Excel():
    def __init__(self, jira, config):
        self.jira = jira
        self.config = config

    @property
    def generated_date(self):
        return self.config['generated'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

    @property
    def title(self):
        return self.config['title']

    @property
    def subject(self):
        return self.config['subject']

    @property
    def font_name(self):
        return self.config['font_name']

    @property
    def font_size(self):
        return self.config['font_size']

    def generate(self) -> None:
        output_file = self.config['output']['report']
        logger.info(f"generating {output_file}")

        book = xlsxwriter.Workbook(output_file)
        book.set_properties({
            'title':    self.title,
            'subject':  self.subject,
            'author':   self.config['author'],
            'manager':  self.config['manager'],
            'company':  self.config['company'],
            'keywords': self.config['keywords'],
            'created':  self.config['generated'],
            'comments': self.config['comments'],
        })
        book.set_size(1600, 1200)

        self.common_format_base = {'font_name': self.font_name, 'font_size': self.font_size, 'align': 'left', 'valign': 'top', 'text_wrap': True, 'border': 1}
        self.common_format = book.add_format(self.common_format_base)

        self.header_format = book.add_format({**self.common_format_base, **{'bold': True, 'font_color': 'white', 'bg_color': 'gray', 'font_size': self.font_size + 2}})

        self.key_format = book.get_default_url_format()
        self.key_format.set_align('top')
        self.key_format.set_border(1)
        self.key_format.set_font_name(self.font_name)
        self.key_format.set_font_size(self.font_size)

        self.bold_format = book.add_format({**self.common_format_base, **{'bold': True}})
        self.summary_format = book.add_format(self.common_format_base)

        for sheet_id, sheet in self.config['sheets'].items():
            generator_method = getattr(self.__class__, sheet['generator'])
            generator_method(self, book)

        logger.info(f"closing file {output_file}")
        book.close()

    #
    # cover
    #
    def add_cover_sheet(self, book: xlsxwriter.Workbook) -> None:
        props = self.config['sheets']['cover']
        logger.info(f"adding cover sheet '{props['name']}'")
        cover = book.add_worksheet(props['name'])

        title_format = book.add_format({'font_name': self.font_name, 'font_size': self.font_size + 10, 'bold': True})
        cover.set_column(0, 0, 120)
        self.write(cover, 0, 0, f"{self.title} {self.subject}", title_format)
        subtitle_format = book.add_format({'font_name': self.font_name, 'font_size': self.font_size + 4, 'bold': True})
        self.write(cover, 1, 0, f"Generated on {self.generated_date}", subtitle_format)
        self.write(cover, 2, 0, props['introduction'])
        # splash = props['splash']
        # cover.insert_image(2, 0, splash['image'], {'object_position': 1, 'x_scale': float(splash['x_scale']), 'y_scale': float(splash['y_scale'])})
        # cover.set_row(2, 200)
        self.set_paper(cover, 3, 1)

    #
    # requirements
    #
    def add_requirements_sheet(self, book: xlsxwriter.Workbook) -> None:
        props = self.config['sheets']['requirements']
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        req_format = book.add_format(self.common_format_base)

        reqs = self.jira.requirements
        logger.info(f'found {len(reqs)} requirements')
        stories = set()
        # requirements, sorted by requirement ID
        row = 1
        for req in self.jira.sorted_by_id(reqs.values()):
            log_issue(req)
            req_row = row

            # directly linked risks
            risks = set(req.risks)

            # stories, sorted by issue key
            story_row = req_row
            for story in self.jira.sorted_by_key(req.stories):
                log_issue(story, 1)
                stories.add(story.key)

                # add to aggregate risks
                if props['aggregate_risks']:
                    risks.update(self.jira.get_issue(story.key).risks)

                # tests, sorted by issue key
                test_row = story_row
                for test in self.jira.sorted_by_key(story.tests):
                    log_issue(test, 2)
                    self.write_key_and_summary(report, test_row, columns['test_key'].column, test)
                    test_row += 1
                if len(story.tests) == 0:
                    self.write_status(report, story_row, columns['test_status'].column, story)

                row = max(story_row + 1, test_row) - 1
                self.write_key_and_summary(report, story_row, columns['story_key'].column, story, end_row = row)
                row += 1

            # risks, sorted by issue key
            risk_row = req_row
            for risk in self.jira.sorted_by_key(risks):
                log_issue(risk, 1)
                self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk)
                risk_row += 1

            row = max(req_row + 1, risk_row, row) - 1
            self.write_id(report, req_row, columns['req_id'].column, req, end_row = row)
            self.write_key_and_summary(report, req_row, columns['req_key'].column, req, end_row = row)
            self.write_html(report, req_row, columns['req_description'].column, req.description, end_row = row)
            row += 1

        report.ignore_errors({ 'number_stored_as_text': f'{self.range_address(0, 0, row - 1, columns.last)}' })
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'found {len(stories)} unique stories')


    #
    # epics
    #
    def add_epics_sheet(self, book: xlsxwriter.Workbook):
        props = self.config['sheets']['epics']
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        epics = self.jira.epics
        logger.info(f'found {len(epics)} epics')
        stories = set()
        # epics, sorted by key
        row = 1
        for epic in self.jira.sorted_by_key(epics.values()):
            log_issue(epic)
            epic_row = row

            # stories within the epic, sorted by key
            for story in self.jira.sorted_by_key(epic.stories):
                log_issue(story, 1)
                story_row = row
                stories.add(story.key)

                # risks within the story, sorted by key
                risk_row = story_row
                for risk in self.jira.sorted_by_key(story.risks):
                    log_issue(risk, 2)
                    self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk)
                    risk_row += 1

                # tests within the story, sorted by key
                test_row = story_row
                for test in self.jira.sorted_by_key(story.tests):
                    log_issue(test, 2)
                    self.write_key_and_summary(report, test_row, columns['test_key'].column, test)
                    test_row += 1

                # include test strategy, if filled in (mostly for legacy stories)
                if story.raw_test_strategy:
                    self.write(report, test_row, columns['test_key'].column, self.prettify_links(story.raw_test_strategy), self.summary_format, end_col = columns['test_summary'].column)
                    if story.is_done:
                        self.write(report, test_row, columns['test_status'].column, PASSED, self.bold_format)
                    elif story.is_blocked:
                        self.write(report, test_row, columns['test_status'].column, BLOCKED, self.bold_format)
                    test_row += 1

                # merge story row to span all risks and tests
                row = max(story_row + 1, risk_row, test_row) - 1
                self.write_key_and_summary(report, story_row, columns['story_key'].column, story, end_row = row)
                row += 1

            # merge epic row to span all stories (including risks and tests within them)
            row = max(epic_row + 1, row) - 1
            self.write_key_and_summary(report, epic_row, columns['epic_key'].column, epic, end_row = row)
            row += 1

        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'found {len(stories)} unique stories')


    #
    # risks
    #
    def add_risks_sheet(self, book: xlsxwriter.Workbook):
        props = self.config['sheets']['risks']
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        risks = self.jira.risks
        logger.info(f'found {len(risks)} risks')
        stories = set()
        # risks, sorted by harm
        row = 1
        for risk in self.jira.sorted_by_harm(risks.values()):
            log_issue(risk)
            risk_row = row

            # stories that mitigate this risk, sorted by key
            story_row = row
            for story in self.jira.sorted_by_key(risk.stories):
                log_issue(story, 1)
                stories.add(story.key)
                self.write_key_and_summary(report, story_row, columns['mitigation_key'].column, story)
                story_row += 1

            row = max(risk_row + 1, story_row) - 1
            self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk, end_row=row)
            self.write(report, risk_row, columns['sequence'].column, risk.sequence, end_row=row)
            self.write(report, risk_row, columns['harm'].column, risk.harm, end_row=row)
            self.write(report, risk_row, columns['hazard'].column, risk.hazard, end_row=row)
            self.write(report, risk_row, columns['initial_severity'].column, risk.initial_severity, end_row=row)
            self.write(report, risk_row, columns['initial_probability'].column, risk.initial_probability, end_row=row)
            self.write(report, risk_row, columns['initial_risk'].column, risk.initial_risk, end_row=row)
            self.write(report, risk_row, columns['residual_severity'].column, risk.residual_severity, end_row=row)
            self.write(report, risk_row, columns['residual_probability'].column, risk.residual_probability, end_row=row)
            self.write(report, risk_row, columns['residual_risk'].column, risk.residual_risk, end_row=row)
            self.write(report, risk_row, columns['benefit'].column, risk.benefit, end_row=row)
            row += 1

        low_format = book.add_format({'bg_color': 'green'})
        high_format = book.add_format({'bg_color': 'red'})
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': 'High', 'format': high_format}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': 'Low', 'format': low_format}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'found {len(stories)} unique stories')

    #
    # helper methods
    #

    @staticmethod
    def prettify_links(text):
        return re.sub(r"""\[.+\|(https?:[^\]\|]+)(?:\|[^\]]+)?\]""", r"""\1""", text)

    @staticmethod
    def cell_address(row: int, col: int) -> str:
        return f"{chr(ord('A') + col)}{row + 1}"

    @staticmethod
    def range_address(start_row: int, start_col: int, end_row: int, end_col: int) -> str:
        return f"{Excel.cell_address(start_row, start_col)}:{Excel.cell_address(end_row, end_col)}"

    def set_headings(self, sheet: xlsxwriter.worksheet, columns: Columns):
        sheet.freeze_panes(columns.row + 1, 0) # freeze header row
        sheet.repeat_rows(columns.row)
        for col in columns.ordered:
            sheet.set_column(col.column, col.column, col.width, self.common_format)
            sheet.write(col.row, col.column, col.label, self.header_format)

    def set_conditional_format(self, sheet: xlsxwriter.worksheet, format: dict, rows: Tuple[int, int], columns: List[Column]) -> None:
        if rows[1] - rows[0] > 0:
            for col in columns:
                sheet.conditional_format(rows[0], col.column, rows[1], col.column, format)

    def merge(self, sheet: xlsxwriter.worksheet, row: int, col: int, end_row: int = None, end_col: int = None, value = '', format: xlsxwriter.format = None) -> bool:
        end_row = end_row or row
        end_col = end_col or col
        if end_row - row > 0 or end_col - col > 0:
            sheet.merge_range(row, col, end_row, end_col, value, format or self.common_format)
            return True
        return False

    def write(self, sheet: xlsxwriter.worksheet, row: int, col: int, value, format: xlsxwriter.format = None, end_row: int = None, end_col: int = None) -> None:
        if not self.merge(sheet, row, col, end_row, end_col, value, format):
            sheet.write(row, col, value, format or self.common_format)

    def write_key_and_summary(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.write_url(sheet, row, col, issue, end_row, end_col)
        self.write(sheet, row, col + 1, issue.raw_summary, self.summary_format, end_row)
        if issue.is_test:
            self.write_status(sheet, row, col + 2, issue, end_row)

    def write_url(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.merge(sheet, row, col, end_row, end_col)
        sheet.write_url(row, col, issue.url, self.key_format, issue.key, issue.url)

    def write_html(self, sheet: xlsxwriter.worksheet, row: int, col: int, value, end_row: int = None, end_col: int = None) -> None:
        html = HtmlToExcel(self.bold_format).parse(value)
        self.write(sheet, row, col, html.rendered, self.summary_format, end_row, end_col)

    def write_status(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None) -> None:
        if issue.is_done:
            self.write(sheet, row, col, PASSED, self.bold_format, end_row)
        elif issue.is_blocked:
            self.write(sheet, row, col, BLOCKED, self.bold_format, end_row)

    def write_id(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.write(sheet, row, col, str(issue.id), self.summary_format, end_row, end_col)

    def set_paper(self, sheet: xlsxwriter.worksheet, rows: int, columns: int) -> None:
        sheet.set_paper(self.config['paper_size'])
        sheet.set_landscape()
        sheet.set_margins(left=self.config['margins']['left'], right=self.config['margins']['right'], top=self.config['margins']['top'], bottom=self.config['margins']['bottom'])
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0)  # 1 page wide and as long as necessary.
        sheet.print_area(0, 0, rows - 1, columns - 1)
        sheet.set_default_row(hide_unused_rows=True)

    def set_header_and_footer(self, sheet: xlsxwriter.worksheet) -> None:
        sheet.set_header(f"""&L&"{self.font_name},Bold"&{self.font_size + 6}{self.title} {self.subject}""" +
                         f"""&C&"{self.font_name},Bold"&{self.font_size + 6}{sheet.name}"""
                         f"""&R&[Picture]""", {'image_right': self.config['images']['logo']})
        sheet.set_footer(f"""&L&"{self.font_name},Regular"&{self.font_size + 2}Generated on {self.generated_date}""" +
                         f"""&RPage &P of &N""")
