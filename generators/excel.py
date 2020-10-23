import logging
from typing import Tuple, List, NamedTuple, Optional
from functools import cached_property
import re
import xlsxwriter
from xlsxwriter.utility import xl_range, xl_cell_to_rowcol, xl_rowcol_to_cell
from enum import IntEnum
from html.parser import HTMLParser

logger = logging.getLogger(__name__)

def log_issue(issue, indent: int = 0):
    logger.debug(f"{indent * '--> '}added {issue.type} {issue.key} {issue.url}")

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
        text = re.sub(r"""https://docs.google.+""", r"Google Document", self.text)
        return re.sub(r"""https://tidepool.atlassian.net/browse/(.+)""", r"\1", text)

    @property
    def is_empty(self):
        return False

    @property
    def rendered(self):
        return self.pretty_link

class HtmlToExcel(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = [ ]

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
    def __init__(self, jira, config: dict):
        self.jira = jira
        self.config = config

    @property
    def generated_date(self):
        return self.config['generated'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

    @property
    def passed(self):
        return self.config['labels']['passed']

    @property
    def blocked(self):
        return self.config['labels']['blocked']

    @property
    def properties(self):
        return self.config['properties']

    @property
    def title(self):
        return self.properties['title']

    @property
    def subject(self):
        return self.properties['subject']

    @property
    def font_name(self):
        return self.config['formats']['base']['font_name']

    @property
    def font_size(self):
        return self.config['formats']['base']['font_size']

    def generate(self) -> List[str]:
        output_file = self.config['output']['report']
        logger.info(f"generating {output_file}")

        book = xlsxwriter.Workbook(output_file)
        book.set_properties({
            'title':    self.title,
            'subject':  self.subject,
            'author':   self.properties['author'],
            'manager':  self.properties['manager'],
            'company':  self.properties['company'],
            'keywords': self.properties['keywords'],
            'created':  self.config['generated'],
            'comments': self.properties['comments'],
        })
        book.set_size(*self.config['window_size'])

        self.common_format = self.add_format(book)
        self.column_header_format = self.add_format(book, self.config['formats']['column_header'])
        self.key_format = self.add_format(book, self.config['formats']['url'])
        self.bold_format = self.add_format(book, self.config['formats']['bold'])
        self.summary_format = self.add_format(book)

        for sheet_id, sheet in self.config['sheets'].items():
            generator_method = getattr(self.__class__, sheet['generator'])
            generator_method(self, book)

        logger.info(f"closing file {output_file}")
        book.close()
        return [ self.config['output']['report'] ]

    #
    # cover
    #
    def add_cover_sheet(self, book: xlsxwriter.Workbook) -> None:
        props = self.config['sheets']['cover']
        logger.info(f"adding cover sheet '{props['name']}'")
        cover = book.add_worksheet(props['name'])

        col = 0
        row = 0
        for i, item in props['items'].items():
            (this_row, this_col) = xl_cell_to_rowcol(item['position'])
            col = max(col, this_col)
            row = max(row, this_row)
            if item.get('text'):
                cover.write(item['position'], self.format_text(cover, item['text']), self.add_format(book, item.get('format', {})))
            elif item.get('image'):
                cover.insert_image(item['position'], item['image'], item['options'])
                cover.set_row(this_row, item['height'])
        cover.set_column(0, 0, props['width'])
        self.set_paper(cover, row + 1, col + 1)

    #
    # requirements
    #
    def add_requirements_sheet(self, book: xlsxwriter.Workbook) -> None:
        props = self.config['sheets']['requirements']
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        req_format = self.add_format(book)

        reqs = self.jira.requirements
        logger.info(f'listing {len(reqs)} requirements')
        stories = set()
        # requirements, sorted by requirement ID
        row = 1
        for req in self.jira.sorted_by_id(reqs.values()):
            log_issue(req)
            req_row = row

            # stories, sorted by issue key
            story_row = req_row
            for story in self.jira.sorted_by_key(req.stories):
                log_issue(story, 1)
                stories.add(story.key)

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
            for risk in self.jira.sorted_by_key(req.risks):
                log_issue(risk, 1)
                self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk)
                risk_row += 1

            row = max(req_row + 1, risk_row, row) - 1
            self.write_id(report, req_row, columns['req_id'].column, req, end_row = row)
            self.write_key_and_summary(report, req_row, columns['req_key'].column, req, end_row = row)
            self.write_html(report, req_row, columns['req_description'].column, req.description, end_row = row)
            row += 1

        report.ignore_errors({ 'number_stored_as_text': xl_range(0, 0, row - 1, columns.last) })
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
        logger.info(f'listing {len(epics)} epics')
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
                if story.test_strategy:
                    self.write_html(report, test_row, columns['test_key'].column, story.test_strategy, end_col = columns['test_summary'].column)
                    if story.is_done:
                        self.write(report, test_row, columns['test_status'].column, self.passed, self.bold_format)
                    elif story.is_blocked:
                        self.write(report, test_row, columns['test_status'].column, self.blocked, self.bold_format)
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
        logger.info(f'listing {len(risks)} risks')
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
            self.write_html(report, risk_row, columns['sequence'].column, risk.sequence, end_row=row)
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

        low_format = self.add_format(book, self.config['formats']['low_risk'])
        medium_format = self.add_format(book, self.config['formats']['medium_risk'])
        high_format = self.add_format(book, self.config['formats']['high_risk'])
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['low'], 'format': low_format}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['medium'], 'format': medium_format}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['high'], 'format': high_format}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'found {len(stories)} unique stories')

    #
    # helper methods
    #

    def add_format(self, book: xlsxwriter.Workbook, *formats: List[dict]):
        format = {**self.config['formats']['base']}
        for fmt in formats:
            format.update(fmt)
        return book.add_format(format)

    def set_headings(self, sheet: xlsxwriter.worksheet, columns: Columns):
        sheet.freeze_panes(columns.row + 1, 0) # freeze header row
        sheet.repeat_rows(columns.row)
        for col in columns.ordered:
            sheet.set_column(col.column, col.column, col.width, self.common_format)
            sheet.write(col.row, col.column, col.label, self.column_header_format)

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
        self.write_html(sheet, row, col + 1, issue.summary, end_row)
        if issue.is_test:
            self.write_status(sheet, row, col + 2, issue, end_row)

    def write_url(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.merge(sheet, row, col, end_row, end_col)
        sheet.write_url(row, col, issue.url, self.key_format, issue.key, issue.url)

    def write_html(self, sheet: xlsxwriter.worksheet, row: int, col: int, value, end_row: int = None, end_col: int = None) -> None:
        html = HtmlToExcel().parse(value)
        self.write(sheet, row, col, html.rendered, self.summary_format, end_row, end_col)

    def write_status(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None) -> None:
        if issue.is_done:
            self.write(sheet, row, col, self.passed, self.bold_format, end_row)
        elif issue.is_blocked:
            self.write(sheet, row, col, self.blocked, self.bold_format, end_row)

    def write_id(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.write(sheet, row, col, str(issue.id), self.summary_format, end_row, end_col)

    def set_paper(self, sheet: xlsxwriter.worksheet, rows: int, columns: int) -> None:
        sheet.set_paper(self.config['page']['paper_size'])
        sheet.set_landscape()
        margins = self.config['page']['margins']
        sheet.set_margins(left=margins['left'], right=margins['right'], top=margins['top'], bottom=margins['bottom'])
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0)  # 1 page wide and as long as necessary.
        sheet.print_area(0, 0, rows - 1, columns - 1)
        # sheet.set_default_row(hide_unused_rows=True)

    def format_text(self, sheet: xlsxwriter.worksheet, text: str) -> str:
        if text:
            return text.format(date=self.generated_date, sheet=sheet.name)
        return ''

    def header_font(self, format: str) -> str:
        format = {**self.config['formats']['base'], **self.config['formats'][format]}
        font_name = f"{format['font_name']},{'Bold' if format['bold'] else 'Regular'}"
        font_size = format['font_size']
        return f'&"{font_name}"&{font_size}'

    def set_header_and_footer(self, sheet: xlsxwriter.worksheet) -> None:
        font = self.header_font('page_header')
        parts = self.config['page']['header']
        sheet.set_header(f"""&L{font}{self.format_text(sheet, parts.get('left'))}""" +
                         f"""&C{font}{self.format_text(sheet, parts.get('center'))}""" +
                         f"""&R&[Picture]""", {'image_right': parts.get('right')})

        font = self.header_font('page_footer')
        parts = self.config['page']['footer']
        sheet.set_footer(f"""&L{font}{self.format_text(sheet, parts.get('left'))}""" +
                         f"""&C{font}{self.format_text(sheet, parts.get('center'))}""" +
                         f"""&R{font}{self.format_text(sheet, parts.get('right'))}""")
