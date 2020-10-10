#!/usr/bin/env python3
import sys
import os
import io
import logging
import logging.config
import argparse
import yaml
from datetime import date
from dotenv import load_dotenv
load_dotenv()

from jira import JiraHelper
from generators import Html, Pdf, Excel, GraphViz

#logging.basicConfig(filename='report.log', filemode='w', level=logging.DEBUG, format='%(asctime)s %(levelname)s [%(name)s] %(message)s', datefmt='%Y-%m-%dT%H:%M:%S')
logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

def read_config(filename: str):
    with open(filename, 'r') as config:
        try:
            return yaml.safe_load(config)
        except yaml.YAMLError as ex:
            logger.fatal(ex)

def main():
    logger.info('Tidepool Report Generator v0.1')
    logger.info('parsing arguments')
    parser = argparse.ArgumentParser(description='Generate Verification Test Report')
    default_config_file = 'report.yml'
    parser.add_argument('--config', help=f'configuration file (default: {default_config_file})', default=default_config_file)

    parser.add_argument('--html', action='store_true', help='generate HTML output')
    parser.add_argument('--pdf', action='store_true', help='generate PDF output from HTML')
    parser.add_argument('--excel', action='store_true', help='generate XLSX output')
    parser.add_argument('--graph', action='store_true', help='generate graph output')

    args = parser.parse_args()
    config = read_config(args.config)
    generated = date.today()
    logger.info('connecting to Jira')
    jira = JiraHelper(config['jira'])
    logger.info('generating outputs')
    if args.html:
        config['html']['generated'] = generated
        Html(jira, config['html']).generate()
    if args.excel:
        config['excel']['generated'] = generated
        Excel(jira, config['excel']).generate()
    if args.graph:
        config['graphviz']['generated'] = generated
        GraphViz(jira, config['graphviz']).generate()
    if args.pdf:
        config['pdf']['generated'] = generated
        Pdf(jira, config['pdf']).generate()
    logger.info('done')

if __name__ == '__main__':
    main()
