"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
import logging
from typing import Tuple, List
from operator import attrgetter
import xlsxwriter
from xlsxwriter.utility import xl_range, xl_cell_to_rowcol, xl_rowcol_to_cell

from .html import HtmlToExcel
from .column import Column
from .columns import Columns
import plugins.output

logger = logging.getLogger(__name__)

def log_issue(issue, indent: int = 0):
    logger.debug(f"{indent * '--> '}added {issue.type} {issue.key} {issue.url}")

class Excel(plugins.output.OutputGenerator):
    key = 'excel'
    flag = '--excel'
    description = 'generate Excel output'
    _alias_ = 'Excel'

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
    def verified(self):
        return self.config['labels']['verified']

    @property
    def properties(self):
        return self.config['properties']

    def generate(self) -> List[str]:
        output_file = self.config['output']['report']
        logger.info(f"generating {output_file}")

        book = xlsxwriter.Workbook(output_file)
        book.set_properties({
            'title':    self.properties['title'],
            'subject':  self.properties['subject'],
            'author':   self.properties['author'],
            'manager':  self.properties['manager'],
            'company':  self.properties['company'],
            'keywords': self.properties['keywords'],
            'created':  self.config['generated'],
            'comments': self.properties['comments'],
        })
        book.set_size(*self.config['window_size'])

        self.formats = { }
        for format_key, format in self.config['formats'].items():
            self.formats[format_key] = self.add_format(book, format)

        for _, sheet in self.config['sheets'].items():
            generator_method = getattr(self.__class__, sheet['generator'])
            generator_method(self, book, sheet)

        book.close()
        logger.info(f"done generating {output_file}")
        return [ output_file ]

    #
    # cover
    #
    def add_cover_sheet(self, book: xlsxwriter.Workbook, props: dict) -> None:
        logger.info(f"adding cover sheet '{props['name']}'")
        cover = book.add_worksheet(props['name'])

        col = 0
        row = 0
        for _, item in props['items'].items():
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
    # requirements report
    #
    def add_requirements_sheet(self, book: xlsxwriter.Workbook, props: dict) -> None:
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # requirements, sorted by requirement ID
        total_requirements = 0
        total_verified = 0
        row = 1
        for req in self.jira.sorted_by_id(self.jira.exclude_junk(self.jira.func_requirements.values(), enforce_versions = False)):
            log_issue(req)
            req_row = row

            # stories, sorted by issue key
            story_row = req_row
            for story in self.jira.sorted_by_key(self.jira.exclude_junk(req.defines, enforce_versions = True)):
                log_issue(story, 1)
                verified = False

                # tests, sorted by issue key
                test_row = story_row
                for test in self.jira.sorted_by_key(story.tests):
                    log_issue(test, 2)
                    self.write_key_and_summary(report, test_row, columns['test_key'].column, test)
                    if test.is_done:
                        verified = True
                    test_row += 1
                if test_row == story_row:
                    self.write_status(report, story_row, columns['test_status'].column, story)
                    if story.is_done:
                        verified = True

                row = max(story_row + 1, test_row) - 1
                self.write_key_and_summary(report, story_row, columns['story_key'].column, story, end_row = row)
                story_row = row + 1

            if verified:
                total_verified += 1

            # risks, sorted by issue key
            risk_row = req_row
            for risk in self.jira.sorted_by_key(self.jira.exclude_junk(req.risks, enforce_versions = False)):
                log_issue(risk, 1)
                self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk)
                risk_row += 1

            row = max(req_row + 1, risk_row, story_row) - 1
            self.write_id(report, req_row, columns['req_id'].column, req, end_row = row)
            self.write_key_and_summary(report, req_row, columns['req_key'].column, req, end_row = row)
            self.write_html(report, req_row, columns['req_description'].column, req.description, end_row = row)
            self.merge(report, req_row, columns['gap'].column, end_row = row)
            row += 1
            total_requirements += 1

        report.ignore_errors({ 'number_stored_as_text': xl_range(0, 0, row - 1, columns.last) })
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'total of {total_requirements} requirements')
        logger.info(f'total of {self.percentage(total_requirements, total_verified)} verified requirements')
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # requirements summary
    #
    def add_requirements_summary_sheet(self, book: xlsxwriter.Workbook, props: dict) -> None:
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # requirements, sorted by requirement ID
        total_requirements = 0
        total_verified = 0
        row = 1
        for req in self.jira.sorted_by_id(self.jira.exclude_junk(self.jira.func_requirements.values(), enforce_versions = False)):
            log_issue(req)
            req_row = row

            # stories, sorted by issue key
            story_row = req_row
            for story in self.jira.sorted_by_key(self.jira.exclude_junk(req.defines, enforce_versions = True)):
                log_issue(story, 1)
                self.write_key_and_summary(report, story_row, columns['story_key'].column, story)
                if story.is_done:
                    self.write(report, story_row, columns['story_status'].column, self.verified, self.formats['bold'])
                story_row += 1

            row = max(req_row + 1, story_row) - 1
            self.write_id(report, req_row, columns['req_id'].column, req, end_row = row)
            self.write_key_and_summary(report, req_row, columns['req_key'].column, req, end_row = row)
            self.write_html(report, req_row, columns['req_description'].column, req.description, end_row = row)
            row += 1
            total_requirements += 1

        report.ignore_errors({ 'number_stored_as_text': xl_range(0, 0, row - 1, columns.last) })
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'total of {total_requirements} requirements')
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # epics
    #
    def add_epics_sheet(self, book: xlsxwriter.Workbook, props: dict):
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # epics, sorted by key
        row = 1
        for epic in self.jira.sorted_by_key(self.jira.exclude_junk(self.jira.epics.values(), enforce_versions = True)):
            log_issue(epic)
            epic_row = row

            # stories within the epic, sorted by key
            for story in self.jira.sorted_by_key(self.jira.exclude_junk(epic.stories, enforce_versions = True)):
                log_issue(story, 1)
                story_row = row

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
                        self.write(report, test_row, columns['test_status'].column, self.passed, self.formats['bold'])
                    elif story.is_blocked:
                        self.write(report, test_row, columns['test_status'].column, self.blocked, self.formats['bold'])
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
        logger.info(f"done adding report sheet '{props['name']}'")


    #
    # risks
    #
    def add_risks_sheet(self, book: xlsxwriter.Workbook, props: dict):
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # risks, sorted by harm
        row = 1
        for risk in self.jira.sorted_by_harm(self.jira.exclude_junk(self.jira.risks.values(), enforce_versions = False)):
            log_issue(risk)
            risk_row = row

            # stories that mitigate this risk, sorted by key
            story_row = row
            for story in self.jira.sorted_by_key(self.jira.exclude_junk(risk.mitigated_by, enforce_versions = False)):
                log_issue(story, 1)
                self.write_key_and_summary(report, story_row, columns['mitigation_key'].column, story)
                story_row += 1

            row = max(risk_row + 1, story_row) - 1
            self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk, end_row = row)
            self.write_html(report, risk_row, columns['sequence'].column, risk.sequence, end_row = row)
            self.write(report, risk_row, columns['source'].column, risk.source, end_row = row)
            self.write(report, risk_row, columns['harm'].column, risk.harm, end_row = row)
            self.write(report, risk_row, columns['hazard_category'].column, risk.hazard_category, end_row = row)
            self.write(report, risk_row, columns['initial_severity'].column, risk.initial_severity, end_row = row)
            self.write(report, risk_row, columns['initial_probability'].column, risk.initial_probability, end_row = row)
            self.write(report, risk_row, columns['initial_risk'].column, risk.initial_risk, end_row = row)
            self.write(report, risk_row, columns['residual_severity'].column, risk.residual_severity, end_row = row)
            self.write(report, risk_row, columns['residual_probability'].column, risk.residual_probability, end_row = row)
            self.write(report, risk_row, columns['residual_risk'].column, risk.residual_risk, end_row = row)
            self.write(report, risk_row, columns['benefit'].column, risk.benefit, end_row = row)
            row += 1

        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['low'], 'format': self.formats['low_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['medium'], 'format': self.formats['medium_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['high'], 'format': self.formats['high_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # risks v2
    #
    def add_risks_sheet_v2(self, book: xlsxwriter.Workbook, props: dict):
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # risks, sorted by harm
        total_risks = 0
        total_initial_scores = self.jira.risk_scores
        total_residual_scores = self.jira.risk_scores
        row = 1
        for risk in self.jira.sorted_by_harm(self.jira.exclude_junk(self.jira.risks.values(), enforce_versions = False)):
            log_issue(risk)
            risk_row = row
            total_risks += 1
            total_initial_scores[risk.score(risk.initial_risk)] += 1
            total_residual_scores[risk.score(risk.residual_risk)] += 1

            # list all mitigations in the sheet
            story_row = row
            for mitigation in self.jira.sorted_by_key(risk.mitigations):
                self.write_key_and_summary(report, story_row, columns['mitigation_key'].column, mitigation)
                story_row += 1

            row = max(risk_row + 1, story_row) - 1
            self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk, end_row = row)
            self.write_html(report, risk_row, columns['sequence'].column, risk.sequence, end_row = row)
            self.write(report, risk_row, columns['source'].column, risk.source, end_row = row)
            self.write(report, risk_row, columns['harm'].column, risk.harm, end_row = row)
            self.write(report, risk_row, columns['hazard'].column, risk.hazard, end_row = row)
            self.write(report, risk_row, columns['hazard_category'].column, risk.hazard_category, end_row = row)
            self.write(report, risk_row, columns['initial_severity'].column, risk.initial_severity, end_row = row)
            self.write(report, risk_row, columns['initial_probability'].column, risk.initial_probability, end_row = row)
            self.write(report, risk_row, columns['initial_risk'].column, risk.initial_risk, end_row = row)
            self.write(report, risk_row, columns['residual_severity'].column, risk.residual_severity, end_row = row)
            self.write(report, risk_row, columns['residual_probability'].column, risk.residual_probability, end_row = row)
            self.write(report, risk_row, columns['residual_risk'].column, risk.residual_risk, end_row = row)
            self.write(report, risk_row, columns['benefit'].column, risk.benefit, end_row = row)
            row += 1

        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['low'], 'format': self.formats['low_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['medium'], 'format': self.formats['medium_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['high'], 'format': self.formats['high_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'total of {total_risks} risks')
        for key, count in total_initial_scores.items():
            logger.info(f'total of initial risk {key.name}: {self.percentage(total_risks, count)} risks')
        for key, count in total_residual_scores.items():
            logger.info(f'total of residual risk {key.name}: {self.percentage(total_risks, count)} risks')
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # insulin fidelity
    #
    def add_insulin_fidelity_sheet(self, book: xlsxwriter.Workbook, props: dict):
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # risks, sorted by harm
        total_risks = 0
        total_initial_scores = self.jira.risk_scores
        total_residual_scores = self.jira.risk_scores
        row = 1
        for risk in self.jira.sorted_by_harm(self.jira.filter_by(self.jira.risks.values(), props['filter'])):
            log_issue(risk)
            risk_row = row
            total_risks += 1
            total_initial_scores[risk.score(risk.initial_risk)] += 1
            total_residual_scores[risk.score(risk.residual_risk)] += 1

            # list all mitigations in the sheet
            story_row = row
            for mitigation in self.jira.sorted_by_key(risk.mitigations):
                stories = set()
                tests = set()
                if mitigation.is_func_requirement:
                    self.write_id(report, story_row, columns['mitigation_id'].column, mitigation)
                    self.write_key_and_summary(report, story_row, columns['mitigation_key'].column, mitigation)
                    for story in mitigation.defines: # add all stories, and all tests that verify those stories
                        stories.add(story)
                        tests.update(story.tests)
                else: # story or IFU
                    stories.add(mitigation)
                    tests.update(mitigation.tests)
                    if len(tests) == 0:
                        tests = stories
                if len(stories) == 1:
                    self.write_key(report, story_row, columns['story_keys'].column, stories.pop())
                else:
                    self.write(report, story_row, columns['story_keys'].column, ', '.join([ story.key for story in self.jira.sorted_by_key(stories) ]))
                self.write(report, story_row, columns['test_keys'].column, ', '.join([ test.key for test in self.jira.sorted_by_key(tests) ]))
                story_row += 1

            row = max(risk_row + 1, story_row) - 1
            self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk, end_row = row)
            # self.write_html(report, risk_row, columns['sequence'].column, risk.sequence, end_row = row)
            # self.write(report, risk_row, columns['source'].column, risk.source, end_row = row)
            # self.write(report, risk_row, columns['harm'].column, risk.harm, end_row = row)
            # self.write(report, risk_row, columns['hazard'].column, risk.hazard, end_row = row)
            self.write(report, risk_row, columns['hazard_category'].column, risk.hazard_category, end_row = row)
            self.write(report, risk_row, columns['initial_severity'].column, risk.initial_severity, end_row = row)
            # self.write(report, risk_row, columns['initial_probability'].column, risk.initial_probability, end_row = row)
            self.write(report, risk_row, columns['initial_risk'].column, risk.initial_risk, end_row = row)
            # self.write(report, risk_row, columns['residual_severity'].column, risk.residual_severity, end_row = row)
            # self.write(report, risk_row, columns['residual_probability'].column, risk.residual_probability, end_row = row)
            self.write(report, risk_row, columns['residual_risk'].column, risk.residual_risk, end_row = row)
            row += 1

        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['low'], 'format': self.formats['low_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['medium'], 'format': self.formats['medium_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['high'], 'format': self.formats['high_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'total of {total_risks} risks')
        for key, count in total_initial_scores.items():
            logger.info(f'total of initial risk {key.name}: {self.percentage(total_risks, count)} risks')
        for key, count in total_residual_scores.items():
            logger.info(f'total of residual risk {key.name}: {self.percentage(total_risks, count)} risks')
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # bugs
    #
    def add_bugs_sheet(self, book: xlsxwriter.Workbook, props: dict):
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # bugs, sorted by key
        row = 1
        for bug in self.jira.sorted_by_fix_version(self.jira.exclude_junk(self.jira.bugs.values(), enforce_versions = False)):
            log_issue(bug)
            bug_row = row

            self.write_key_and_summary(report, bug_row, columns['bug_key'].column, bug, end_row = row)
            self.write_status(report, bug_row, columns['bug_status'].column, bug, end_row = row)
            self.write(report, bug_row, columns['fix_version'].column, ', '.join(bug.fix_versions), end_row = row)
            row += 1

        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # tests
    #
    def add_tests_sheet(self, book: xlsxwriter.Workbook, props: dict):
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # tests
        row = 1
        for test_report in self.test_reports.reports.values():
            for test in sorted(test_report.test_cases, key = attrgetter('suite', 'name')):
                self.write(report, row, columns['test_suite'].column, test.suite)
                self.write(report, row, columns['test_case'].column, test.name)
                self.write(report, row, columns['time'].column, test.time)
                self.write(report, row, columns['status'].column, self.passed if test.status else '', self.formats['bold'])
                row += 1

        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # helper methods
    #

    def percentage(self, total, count) -> str:
        total = total if total > 0 else 1
        return f'{count} ({round(float(count) / total * 100, 2)}%)'

    def add_format(self, book: xlsxwriter.Workbook, *formats: List[dict]):
        format = {**self.config['formats']['base']}
        for fmt in formats:
            format.update(fmt)
        return book.add_format(format)

    def set_headings(self, sheet: xlsxwriter.worksheet, columns: Columns):
        sheet.freeze_panes(columns.row + 1, 0) # freeze header row
        sheet.repeat_rows(columns.row)
        for col in columns.ordered:
            sheet.set_column(col.column, col.column, col.width, self.formats['base'])
            sheet.write(col.row, col.column, col.label, self.formats['column_header'])

    def set_conditional_format(self, sheet: xlsxwriter.worksheet, format: dict, rows: Tuple[int, int], columns: List[Column]) -> None:
        if rows[1] - rows[0] > 0:
            for col in columns:
                sheet.conditional_format(rows[0], col.column, rows[1], col.column, format)

    def merge(self, sheet: xlsxwriter.worksheet, row: int, col: int, end_row: int = None, end_col: int = None, value = '', format: xlsxwriter.format = None) -> bool:
        end_row = end_row or row
        end_col = end_col or col
        if end_row - row > 0 or end_col - col > 0:
            sheet.merge_range(row, col, end_row, end_col, value, format or self.formats['base'])
            return True
        return False

    def write(self, sheet: xlsxwriter.worksheet, row: int, col: int, value, format: xlsxwriter.format = None, end_row: int = None, end_col: int = None) -> None:
        if not self.merge(sheet, row, col, end_row, end_col, value, format):
            sheet.write(row, col, value, format or self.formats['base'])

    def write_key_and_summary(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.write_key(sheet, row, col, issue, end_row, end_col)
        self.write_html(sheet, row, col + 1, issue.summary, end_row)
        if issue.is_test:
            self.write_status(sheet, row, col + 2, issue, end_row)

    def write_key(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.write_url(sheet, row, col, issue, end_row, end_col)

    def write_url(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.merge(sheet, row, col, end_row, end_col)
        sheet.write_url(row, col, issue.url, self.formats['url'], issue.key, issue.url)

    def write_html(self, sheet: xlsxwriter.worksheet, row: int, col: int, value, end_row: int = None, end_col: int = None) -> None:
        html = HtmlToExcel().parse(value)
        self.write(sheet, row, col, html.rendered, self.formats['summary'], end_row, end_col)

    def write_status(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None) -> None:
        if issue.is_done:
            self.write(sheet, row, col, self.passed, self.formats['bold'], end_row)
        elif issue.is_blocked:
            self.write(sheet, row, col, self.blocked, self.formats['bold'], end_row)

    def write_id(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None, end_col: int = None) -> None:
        self.write(sheet, row, col, str(issue.id), self.formats['summary'], end_row, end_col)

    def set_paper(self, sheet: xlsxwriter.worksheet, rows: int, columns: int) -> None:
        sheet.set_paper(self.config['page']['paper_size'])
        sheet.set_landscape()
        margins = self.config['page']['margins']
        sheet.set_margins(left = margins['left'], right = margins['right'], top = margins['top'], bottom = margins['bottom'])
        sheet.center_horizontally()
        sheet.fit_to_pages(1, 0)  # 1 page wide and as long as necessary.
        sheet.print_area(0, 0, rows - 1, columns - 1)
        sheet.set_default_row(hide_unused_rows = True)

    def format_text(self, sheet: xlsxwriter.worksheet, text: str) -> str:
        if text:
            return text.format(date = self.generated_date, sheet = sheet.name)
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
