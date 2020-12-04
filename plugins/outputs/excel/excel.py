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
from ...inputs.jira import JiraRiskScore

logger = logging.getLogger(__name__)

def log_issue(issue, indent: int = 0):
    logger.debug(f"{indent * '--> '}added {issue.type} {issue.key} {issue.url}")

class Excel(plugins.output.OutputGenerator):
    key = 'excel'
    flag = '--excel'
    description = 'generate Excel output'
    _alias_ = 'Excel'

    @property
    def labels(self):
        return self.config['labels']

    @property
    def generated_date(self):
        return self.config['generated'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')

    @property
    def passed(self):
        return self.labels['passed']

    @property
    def blocked(self):
        return self.labels['blocked']

    @property
    def verified(self):
        return self.labels['verified']

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
    # requirements
    #
    def add_requirements_sheet(self, book: xlsxwriter.Workbook, props: dict) -> None:
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # requirements, sorted by requirement ID
        req_ids = { }
        row = 1
        for req in self.jira.sorted_by_id(self.jira.exclude_junk(self.jira.func_requirements.values(), enforce_versions = False)):
            log_issue(req)

            self.write_id(report, row, columns['req_id'].column, req)
            self.write_key_and_summary(report, row, columns['req_key'].column, req)
            self.write_html(report, row, columns['req_description'].column, req.description)
            row += 1
            # uniqueness check; requirement IDs should be globally unique
            if req.id in req_ids:
                logger.warn(f"requirement ID '{req.id}' duplicated in: {', '.join([ *req_ids[req.id], req.key ])}")
                req_ids[req.id].append(req.key)
            else:
                req_ids[req.id] = [ req.key ]

        report.ignore_errors({ 'number_stored_as_text': xl_range(0, 0, row - 1, columns.last) })
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        logger.info(f'total of {len(req_ids)} requirements')
        dupes = { req_id: req_keys for req_id, req_keys in req_ids.items() if len(req_keys) > 1 }
        if len(dupes) > 0:
            logger.warn(f"total of {len(dupes)} duplicated requirement IDs: {', '.join(dupes.keys())}")
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # traceability report (full and not-so-full)
    #
    def add_traceability_sheet(self, book: xlsxwriter.Workbook, props: dict) -> None:
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
            verified = False
            story_row = req_row
            for story in self.jira.sorted_by_key(self.jira.exclude_junk(req.defines, enforce_versions = True)):
                log_issue(story, 1)

                # tests, sorted by issue key
                test_row, tests_verified = self.write_tests(report, story_row, columns['test_key'].column, story)

                # update verification status
                verified = verified or story.is_done or tests_verified

                # story summary, possibly across many rows
                row = max(story_row + 1, test_row) - 1
                self.write_key_and_summary(report, story_row, columns['story_key'].column, story, end_row = row)
                self.set_outline(report, story_row, req_row, 1)
                story_row = row + 1

            if verified:
                total_verified += 1

            risk_row = req_row
            if columns.get('risk_key'): # include risks?
                risk_row, mitigated = self.write_risks(report, risk_row, columns['risk_key'].column, req)

            row = max(req_row + 1, risk_row, story_row) - 1
            self.write_id(report, req_row, columns['req_id'].column, req, end_row = row)
            self.write_key_and_summary(report, req_row, columns['req_key'].column, req, end_row = row)
            self.write_html(report, req_row, columns['req_description'].column, req.description, end_row = row)
            if columns.get('gap'):
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
    # traceability summary
    #
    def add_traceability_summary_sheet(self, book: xlsxwriter.Workbook, props: dict) -> None:
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'])
        self.set_headings(report, columns)

        # requirements, sorted by requirement ID
        total_requirements = 0
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
                self.set_outline(report, story_row, req_row, 1)
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
    # epics (not used)
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
                risk_row, mitigated = self.write_risks(report, story_row, columns['risk_key'].column, story)

                # tests within the story, sorted by key
                test_row, verified = self.write_tests(report, story_row, columns['test_key'].column, story)

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
    # risks (aka Hazard Analysis)
    #
    def add_risks_sheet(self, book: xlsxwriter.Workbook, props: dict):
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'], row = 6) # start from row 6 (zero-based) to leave room for risk summary
        self.set_headings(report, columns)

        # risks, sorted by harm
        total_risks = 0
        total_initial_scores = self.jira.risk_scores
        total_residual_scores = self.jira.risk_scores
        row = 7
        for risk in self.jira.sorted_by_harm(self.jira.exclude_junk(self.jira.risks.values(), enforce_versions = False)):
            log_issue(risk)
            risk_row = row
            total_risks += 1
            total_initial_scores[risk.score(risk.initial_risk, 'initial')] += 1
            total_residual_scores[risk.score(risk.residual_risk, 'residual')] += 1

            # list all mitigations in the sheet
            story_row = row
            for mitigation in self.jira.sorted_by_key(risk.mitigations):
                self.write_key_and_summary(report, story_row, columns['mitigation_key'].column, mitigation)
                logger.debug(f"""{mitigation.key}: '{mitigation.description}'""")
                self.write_html(report, story_row, columns['mitigation_description'].column, mitigation.description)
                self.set_outline(report, story_row, row, 1)
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
        self.write_risk_summary(report, 0, total_risks, total_initial_scores, columns['initial_risk'].column, total_residual_scores, columns['residual_risk'].column)
        logger.info(f"done adding report sheet '{props['name']}'")

    #
    # insulin fidelity
    #
    def add_insulin_fidelity_sheet(self, book: xlsxwriter.Workbook, props: dict):
        logger.info(f"adding report sheet '{props['name']}'")
        report = book.add_worksheet(props['name'])
        columns = Columns(props['columns'], row = 6) # start from row 6 (zero-based) to leave room for risk summary
        self.set_headings(report, columns)

        # risks, sorted by harm
        total_risks = 0
        total_initial_scores = self.jira.risk_scores
        total_residual_scores = self.jira.risk_scores
        row = 7
        for risk in self.jira.sorted_by_harm(self.jira.filter_by(self.jira.risks.values(), props['filter'])):
            log_issue(risk)
            risk_row = row
            total_risks += 1
            total_initial_scores[risk.score(risk.initial_risk, 'initial')] += 1
            total_residual_scores[risk.score(risk.residual_risk, 'residual')] += 1

            # list all mitigations in the sheet
            story_row = row
            for mitigation in self.jira.sorted_by_key(risk.mitigations):
                stories = set()
                tests = set()
                if mitigation.is_func_requirement:
                    self.write_id(report, story_row, columns['mitigation_id'].column, mitigation)
                    self.write_html(report, story_row, columns['mitigation_description'].column, mitigation.description)
                    for story in mitigation.defines: # add all stories, and all tests that verify those stories
                        stories.add(story)
                        tests.update(story.tests)
                else: # story or IFU
                    stories.add(mitigation)
                    tests.update(mitigation.tests)
                if len(tests) == 0: # if there are no tests, then the stories cover the testing
                    tests = stories
                self.write(report, story_row, columns['story_keys'].column, ', '.join([ story.key for story in self.jira.sorted_by_key(stories) ]))
                self.write(report, story_row, columns['test_keys'].column, ', '.join([ test.key for test in self.jira.sorted_by_key(tests) ]))
                self.set_outline(report, story_row, row, 1)
                story_row += 1

            row = max(risk_row + 1, story_row) - 1
            self.write_key_and_summary(report, risk_row, columns['risk_key'].column, risk, end_row = row)
            self.write(report, risk_row, columns['hazard'].column, risk.hazard, end_row = row)
            self.write(report, risk_row, columns['hazard_category'].column, risk.hazard_category, end_row = row)
            self.write(report, risk_row, columns['initial_severity'].column, risk.initial_severity, end_row = row)
            self.write(report, risk_row, columns['initial_risk'].column, risk.initial_risk, end_row = row)
            self.write(report, risk_row, columns['residual_risk'].column, risk.residual_risk, end_row = row)
            row += 1

        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['low'], 'format': self.formats['low_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['medium'], 'format': self.formats['medium_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_conditional_format(report, {'type': 'text', 'criteria': 'containing', 'value': self.config['risks']['high'], 'format': self.formats['high_risk']}, (1, row - 1), columns.find_all('initial_risk', 'residual_risk'))
        self.set_paper(report, row, len(columns))
        self.set_header_and_footer(report)
        self.write_risk_summary(report, 0, total_risks, total_initial_scores, columns['initial_risk'].column, total_residual_scores, columns['residual_risk'].column)
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
        self.set_autofilter(report, row, len(columns))
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
        for report_name, test_report in self.test_reports.reports.items():
            for test in sorted(test_report.test_cases, key = attrgetter('suite', 'name')):
                self.write(report, row, columns['test_report'].column, report_name)
                self.write(report, row, columns['test_suite'].column, test.suite)
                self.write(report, row, columns['test_case'].column, test.name)
                self.write(report, row, columns['time'].column, test.time)
                self.write(report, row, columns['status'].column, self.passed if test.status else '', self.formats['bold'])
                row += 1

        self.set_paper(report, row, len(columns))
        self.set_autofilter(report, row, len(columns))
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

    def set_outline(self, sheet: xlsxwriter.worksheet, row: int, start_row: int, level: int = 1) -> None:
        if row > start_row:
            sheet.set_row(row, options = { 'level': level })

    def set_autofilter(self, sheet: xlsxwriter.worksheet, rows: int, cols: int) -> None:
        sheet.autofilter(0, 0, rows - 1, cols - 1)

    def write_tests(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue) -> Tuple[int, bool]:
        test_row = row
        verified = False
        for test in self.jira.sorted_by_key(issue.tests):
            self.write_key_and_summary(sheet, test_row, col, test)
            verified = verified or test.is_done
            self.set_outline(sheet, test_row, row, 1)
            test_row += 1
        if test_row == row: # there were no Xray tests
            self.write_key(sheet, test_row, col, issue)
            self.write(sheet, test_row, col + 1, self.labels['see_test_strategy'].format(story_key = issue.key))
            self.write_status(sheet, test_row, col + 2, issue)
            verified = verified or issue.is_done
        return ( test_row, verified )

    def write_risks(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue) -> Tuple[int, bool]:
        risk_row = row
        mitigated = False
        for risk in self.jira.sorted_by_key(self.jira.exclude_junk(issue.risks, enforce_versions = False)):
            self.write_key_and_summary(sheet, risk_row, col, risk)
            mitigated = mitigated or risk.is_done
            self.set_outline(sheet, risk_row, row, 1)
            risk_row += 1
        return ( risk_row, mitigated )

    def write_risk_summary(self, sheet: xlsxwriter.worksheet, start_row: int, total_risks: int, initial_risk_scores: dict, initial_risk_column: int, residual_risk_scores: dict, residual_risk_column: int) -> None:
        logger.info(f'total of {total_risks} risks')
        formats = {
            JiraRiskScore.GREEN: self.formats['low_risk'],
            JiraRiskScore.YELLOW: self.formats['medium_risk'],
            JiraRiskScore.RED: self.formats['high_risk'],
            JiraRiskScore.UNKNOWN: self.formats['unknown_risk'],
        }
        row = start_row
        for key, count in initial_risk_scores.items():
            logger.info(f'total of initial risk {key.name}: {self.percentage(total_risks, count)} risks')
            self.write(sheet, row, initial_risk_column, self.percentage(total_risks, count), formats[key])
            row += 1
        self.write(sheet, row, initial_risk_column, self.percentage(total_risks, total_risks), self.formats['bold'])
        row = start_row
        for key, count in residual_risk_scores.items():
            logger.info(f'total of residual risk {key.name}: {self.percentage(total_risks, count)} risks')
            self.write(sheet, row, residual_risk_column, self.percentage(total_risks, count), formats[key])
            row += 1
        self.write(sheet, row, residual_risk_column, self.percentage(total_risks, total_risks), self.formats['bold'])

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
        if self.config['links']:
            sheet.write_url(row, col, issue.url, self.formats['url'], issue.key, issue.url)
        else:
            sheet.write(row, col, issue.key, self.formats['base'])

    def write_html(self, sheet: xlsxwriter.worksheet, row: int, col: int, value, end_row: int = None, end_col: int = None) -> None:
        html = HtmlToExcel().parse(value)
        self.write(sheet, row, col, html.rendered, self.formats['summary'], end_row, end_col)

    def write_status(self, sheet: xlsxwriter.worksheet, row: int, col: int, issue, end_row: int = None) -> None:
        if issue.is_done:
            self.write(sheet, row, col, self.passed, self.formats['bold'], end_row)
        elif issue.is_blocked:
            self.write(sheet, row, col, self.blocked, self.formats['bold'], end_row)
        else:
            self.write(sheet, row, col, issue.status, end_row = end_row)

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
        # sheet.set_default_row(hide_unused_rows = True)
        sheet.outline_settings(visible = True, symbols_below = False, symbols_right = False, auto_style = False)

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
