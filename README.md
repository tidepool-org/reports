# README

This repo contains a Python script that can generate various reports from Tidepool's Jira project management tool.

[![Build Status](https://travis-ci.com/tidepool-org/reports.svg?branch=main)](https://travis-ci.com/tidepool-org/reports)

## Installation

This tool uses some features available in Python 3.8 or later.

```shell
$ git clone https://github.com/tidepool-org/reports.git
$ cd reports
$ pip3 install -r requirements.txt
```

If you plan to generate PDF or GraphViz outputs, you'll need to follow the additional installation instructions here:

* `pdfkit`: https://github.com/JazzCore/python-pdfkit
* `graphviz`: https://github.com/xflr6/graphviz

## Usage

This tool uses environment variables `JIRA_BASE_URL`, `JIRA_USERNAME`, and `JIRA_API_TOKEN` to configure the Jira API access. You can either set the variables in shell, or add them to the local `.env` file in the same folder as the tool. Do not add credentials to this repository.

Go to your [Atlassian account security settings](https://id.atlassian.com/manage-profile/security) to create a new Jira API token.

```shell
$ export JIRA_USERNAME={username}
$ export JIRA_API_TOKEN={token}
$ python3 report.py --help
usage: report.py [--version] [-h] [--verbose] [--config CONFIG] [--refresh] [--cache] [--zip] [--tag TAG] [--d3js] [--excel] [--graphviz] [--html] [--pdf]

Generate Tidepool Loop reports

general options:
  --version             show version information
  -h, --help            show this help message and exit
  --verbose, --no-verbose
                        enable verbose mode
  --config CONFIG       configuration file (default: ./config/report.yml)
  --refresh, --no-refresh
                        force a refresh of cached data
  --cache, --no-cache   cache data
  --zip, --no-zip       combine output files into a ZIP file
  --tag TAG             set arbitrary tag for use by templates

output options:
  --d3js                generate D3.js output
  --excel               generate Excel output
  --graphviz            generate GraphViz output
  --html                generate HTML output
  --pdf                 generate PDF output from HTML
```

## Development

The tool uses several Python libraries to do the actual work. See `requirements.txt` for the details.

The script is structured as follows:

```
|- dodo.py          # doit recipes
|- report.py        # main script
|- plugins          # all plug-ins
|  |- input.py      # input source plug-in base class
|  |- output.py     # output generator plug-in base class
|  |- inputs/*.py   # input source plug-ins
|  |- outputs/*.py  # output generator plug-ins
|- templates        # template files
|  |- *.*
|- config
|  |- report.yml    # app configuration file
|  |- logging.conf  # logging configuration file
|  |- inputs/*.yml  # input source configuration files
|  |- outputs/*.yml # output generator configuration files
|- scripts          # utility scripts
|- cache            # cached input files (Jira data, test reports)
|- output           # generated output files
```

## Templates

The `templates` subfolder contains several Jinja2 template files that are used for the HTML output. See the Jinja2 documentation for more guidance on the templating language.

## Docker

You can create a Docker image that contains this tool. Simply run the script to do so:

```shell
$ scripts/dockerize.sh
```

Then you can launch a Docker container to run the tool:

```shell
$ scripts/run-docker.sh
```

It will send the output to a folder named `output`.
