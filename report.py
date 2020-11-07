#!/usr/bin/env python3
import sys
import os
import io
import logging
import logging.config
import argparse
import yaml
from yamlinclude import YamlIncludeConstructor
YamlIncludeConstructor.add_to_loader_class(loader_class = yaml.SafeLoader, base_dir = '.')
from zipfile import ZipFile, ZIP_DEFLATED
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from plugins import plugin_loader

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
    parser = argparse.ArgumentParser(description = 'Generate Tidepool Loop reports')
    default_config_file = 'report.yml'
    parser.add_argument('--config', help = f'configuration file (default: {default_config_file})', default = default_config_file)
    parser.add_argument('--refresh', action = 'store_true', help = 'force a refresh of cached data')
    parser.add_argument('--cache', '--no-cache', dest = 'cache', default = True, action = NegateAction, nargs = 0, help = 'cache data')
    parser.add_argument('--zip', '--no-zip', dest = 'zip', default = True, action = NegateAction, nargs = 0, help = 'combine output files into a ZIP file')

    # add command line flags for each of the output generators
    for plugin in plugin_loader.plugins.output.values():
        logger.debug(f'adding command line flag {plugin.flag} for plugin {plugin.name}')
        parser.add_argument(plugin.flag, dest = 'outputs', action = 'append_const', const = plugin.name, help = plugin.description)

    args = parser.parse_args()
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
        files.update(plugin({ 'generated': generated, **config[plugin.key] }, inputs).generate())

    if args.zip:
        logger.info(f"generating ZIP file {config['zip']['output']} from {files}")
        with ZipFile(config['zip']['output'], mode = 'w', compression = ZIP_DEFLATED) as zip:
            for file in files:
                zip.write(file, arcname = os.path.basename(file))

    logger.info(f"done, elapsed time {datetime.today() - generated}")

if __name__ == '__main__':
    main()
