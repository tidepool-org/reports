#!/usr/bin/env python3
import sys
import os
import io
import logging
import logging.config
import argparse
import yaml
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from jira import JiraHelper
from generators import Html, Pdf, Excel, GraphViz

#logging.basicConfig(filename='report.log', filemode='w', level=logging.DEBUG, format='%(asctime)s %(levelname)s [%(name)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
logging.config.fileConfig('logging.conf')
logger = logging.getLogger('report')

def read_config(filename: str):
    with open(filename, 'r') as config:
        try:
            return yaml.safe_load(config)
        except yaml.YAMLError as ex:
            logger.fatal(ex)

class NegateAction(argparse.Action):
    def __call__(self, parser, ns, values, option):
        setattr(ns, self.dest, option[2:4] != 'no')

def main():
    logger.info('Tidepool Report Generator v0.1')
    logger.debug('parsing arguments')
    parser = argparse.ArgumentParser(description='Generate Verification Test Report')
    default_config_file = 'report.yml'
    parser.add_argument('--config', help=f'configuration file (default: {default_config_file})', default=default_config_file)

    parser.add_argument('--html', action='store_true', help='generate HTML output')
    parser.add_argument('--pdf', action='store_true', help='generate PDF output from HTML')
    parser.add_argument('--excel', action='store_true', help='generate XLSX output')
    parser.add_argument('--graph', action='store_true', help='generate graph output')
    parser.add_argument('--cache', '--no-cache', dest='cache', default=True, action=NegateAction, nargs=0, help='cache data')
    parser.add_argument('--zip', '--no-zip', dest='zip', default=True, action=NegateAction, nargs=0, help='combine output files into a ZIP file')

    args = parser.parse_args()
    config = read_config(args.config)
    generated = datetime.today()
    logger.debug('connecting to Jira')
    jira = JiraHelper(config['jira'])
    logger.info('generating outputs')
    files = [ ]

    if args.html:
        config['html']['generated'] = generated
        files.extend(Html(jira, config['html']).generate())

    if args.excel:
        config['excel']['generated'] = generated
        files.extend(Excel(jira, config['excel']).generate())

    if args.graph:
        config['graphviz']['generated'] = generated
        files.extend(GraphViz(jira, config['graphviz']).generate())

    if args.pdf:
        config['pdf']['generated'] = generated
        files.extend(Pdf(jira, config['pdf']).generate())

    if args.zip:
        logger.info(f"generating ZIP file {config['zip']['output']} from {files}")
        with ZipFile(config['zip']['output'], mode='w', compression=ZIP_DEFLATED) as zip:
            for file in files:
                zip.write(file, arcname=os.path.basename(file))

    logger.debug(f"missed {len(jira.missed)}: {jira.missed.keys()}")
    logger.info(f"done, elapsed time {datetime.today() - generated}")

if __name__ == '__main__':
    main()
