#!/usr/bin/env python3
"""
Report Generator

This Python script reads data from Tidepool's Jira instance (https://tidepool.atlassian.net)
and automated test reports generated by CircleCI, and produces one or more reports, charts,
or graphs based on that data.

The `plugins` folder contains all input and output plug-ins.
The `templates` folder contains templates used by those plug-ins.
The `report.yml` file contains configuration for those plug-ins.

Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
import os
import logging
import logging.config
import argparse
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from dotenv import load_dotenv
import yaml
from yamlinclude import YamlIncludeConstructor
from plugins import plugin_loader

VERSION = '1.0'
BASE_DIR = os.path.dirname(__file__)
CONF_DIR = os.path.join(BASE_DIR, 'config')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
YamlIncludeConstructor.add_to_loader_class(loader_class = yaml.SafeLoader, base_dir = CONF_DIR)
load_dotenv()

os.makedirs(OUTPUT_DIR, exist_ok = True)
logging.config.fileConfig(os.path.join(CONF_DIR, 'logging.conf'))
logger = logging.getLogger('report')

def read_config(filename: str):
    """
    Read the configuration file (YAML)
    """
    with open(filename, 'r') as config:
        try:
            return yaml.safe_load(config)
        except yaml.YAMLError as ex:
            logger.fatal(ex)

class VersionAction(argparse.Action):
    """
    Show version information
    """
    def __call__(self, parser, ns, values, option = None):
        print(VERSION)
        exit(1)

class HelpAction(argparse.Action):
    """
    Show argument help
    """
    def __call__(self, parser, ns, values, option = None):
        parser.print_help()
        exit(1)

class NegateAction(argparse.Action):
    """
    Creates a negated version of a command line flag: "--foo" --> "--no-foo"
    """
    def __call__(self, parser, ns, values, option = None):
        setattr(ns, self.dest, option[2:4] != 'no')

def main():
    """
    Main function
    """
    parser = argparse.ArgumentParser(description = 'Generate Tidepool Loop reports', add_help = False)
    default_config_file = os.path.join(CONF_DIR, 'report.yml')
    group = parser.add_argument_group('general options')
    group.add_argument('--version', action = VersionAction, nargs = 0, help = 'show version information')
    group.add_argument('-h', '--help', action = HelpAction, nargs = 0, help = 'show this help message and exit')
    group.add_argument('--verbose', '--no-verbose', action = NegateAction, nargs = 0, help = 'enable verbose mode')
    group.add_argument('--config', help = f'configuration file (default: {default_config_file})', default = default_config_file)
    group.add_argument('--refresh', '--no-refresh', dest = 'refresh', default = False, action = NegateAction, nargs = 0, help = 'force a refresh of cached data')
    group.add_argument('--cache', '--no-cache', dest = 'cache', default = True, action = NegateAction, nargs = 0, help = 'cache data')
    group.add_argument('--zip', '--no-zip', dest = 'zip', default = True, action = NegateAction, nargs = 0, help = 'combine output files into a ZIP file')
    group.add_argument('--tag', action = 'store', nargs = 1, help = 'set arbitrary tag for use by templates')

    # add command line flags for each of the output generators
    group = parser.add_argument_group('output options')
    for plugin in plugin_loader.plugins.output.values():
        logger.debug(f'adding command line flag {plugin.flag} for plugin {plugin.name}')
        group.add_argument(plugin.flag, dest = 'outputs', action = 'append_const', const = plugin.name, help = plugin.description)

    args = parser.parse_args()
    if args.verbose:
        logger.info(f'Tidepool Report Generator v{VERSION}')
        logger.info('Copyright (c) 2020 Tidepool Project')
    logger.debug('parsing arguments')

    config = read_config(args.config)
    generated = datetime.today()

    # initialize input sources
    logger.debug('connecting to input sources')
    inputs = { }
    for plugin in plugin_loader.plugins.input.values():
        logger.debug(f'connecting to {plugin.name}')
        inputs[plugin.key] = plugin({ 'generated': generated, 'refresh_cache': args.refresh, **config[plugin.key] })

    logger.debug('execute selected output generators')
    files = set()
    for plugin_name in (args.outputs or [ ]):
        plugin = plugin_loader.get_plugin('output', plugin_name)
        logger.info(f'generating {plugin.name} output')
        files.update(plugin({ 'generated': generated, **config[plugin.key], 'tag': args.tag }, inputs).generate())
        logger.info(f'done generating {plugin.name} output')

    if args.zip:
        logger.info(f"generating ZIP file {config['zip']['output']} from {files}")
        with ZipFile(config['zip']['output'], mode = 'w', compression = ZIP_DEFLATED) as zipfile:
            for file in files:
                zipfile.write(file, arcname = os.path.basename(file))

    logger.info(f"done, elapsed time {datetime.today() - generated}")

if __name__ == '__main__':
    main()
