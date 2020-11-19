# README

This repo contains a Python script that can generate various reports from Tidepool's Jira project management tool.

[![Build Status](https://travis-ci.com/tidepool-org/reports.svg?branch=main)](https://travis-ci.com/tidepool-org/reports)

## Reports

This covers the reports found in the Excel output.

The reports pull data from the following Jira projects related to Tidepool Loop:

| Key | Description |
| --- | ----------- |
| [`TLFR`](https://tidepool.atlassian.net/projects/TLFR) | Functional (and User) Requirements |
| [`TLR`](https://tidepool.atlassian.net/projects/TLR) | Risks |
| [`LOOP`](https://tidepool.atlassian.net/projects/LOOP) | Development Stories, Tests and Bugs |
| [`IFU`](https://tidepool.atlassian.net/projects/IFU) | Instructions for Use |

The Jira [JQL](https://www.atlassian.com/software/jira/guides/expand-jira/jql#advanced-search) queries that are used to find the basic lists of issues can be found in the [`jira.yml`](config/inputs/jira.yml) configuration file, along with some parameters that are shared across queries. Here are notable parameters used in those queries:

```
filters:
  junk_resolution: [ 'Duplicate', "Won't Do", 'Deprecated', 'Cannot Reproduce' ]
  done_status: [ 'Waiting for Approval', 'Waiting for Deployment', 'Closed' ]
  blocked_status: [ 'Blocked' ]
parameters:
  fix_version: 'FDA 510(k) Sub'
  include_component: 'iAGC'
  exclude_component: 'ExcludeFromReport'
```

### Traceability Summary

This sheet shows a summary of the tracebility matrix that starts from a functional requirement and traces it to its implementation. Here is how it is built:

1. Get a list of all `TLFR` issues (=functional requirements), regardless of `fix_version`, that have `Dev Ready` or `Active` status.

2. Filter out any that are closed as `junk_resolution`.

3. Sort the list in ascending order by requirement ID, which is one or more decimal numbers separated by dots (ie. `1.10.1` appears after `1.9.2`).

4. List the `TLFR` issues. For each of them:

    1. Get a list of all LOOP issues (=development tasks) that are linked to the requirement with a `defines` relationship **and** matches the `fix_version`.
    
    2. Filter out any that are closed as `junk_resolution`.

    3. Sort the list by issue key, which is the project key (`LOOP`) followed by a decimal number (ie. `LOOP-123` appears after `LOOP-21`).
    
    4. List each task. If it has `done_status`, mark it as "✅ VERIFIED"

### Traceability Report

This sheet shows a more detailed version of the tracebility matrix. It is built in the same way as the summary report above, with the addition of tests executed to verify the development tasks and therefore the functional requirement. Here are the additional steps:

1. For each LOOP issue (=development task):

    1. Get a list of all tests that are linked to the LOOP development task. Tests are also in the LOOP project, but have different issue type.

    2. Sort the list by issue key, which is the project key (`LOOP`) followed by a decimal number (ie. `LOOP-123` appears after `LOOP-21`).

    3. List each test. If it has `done_status`, mark it as "✅ PASSED". If it has `blocked_status`, mark it as "❌ BLOCKED"

### Full Traceability Report

This sheet shows a fully detailed version of the tracebility matrix. It is built in the same way as the traceability report above, with the addition of risks. Here are the additional steps:

1. For each `TLFR` issue (=functional requirement):

    1. Get a list of all TLR issues (=risks) that are linked to that requirement with a `mitigates` relationship. This includes both risks directly linked to the `TLFR` issue, as well as any risks linked to any of the LOOP issues that are defined by that `TLFR` issue. Each `TLR` issue will appear only once in the list.

    2. Sort the list by issue key, which is the project key (`TLR`) followed by a decimal number (ie. `TLR-123` appears after `TLR-21`).

    3. List each risk.

### Hazard Analysis

This sheet shows a hazard analysis, starting from the risks and tracing through the initial risk score, mitigations, and the residual risk score. Here are the steps:

1. Get list of all `TLR` issues (=risks), regardless of `fix_verson`.

2. Filter out any that are closed as `junk_resolution`.

3. Sort the list by the harm caused by that risk.

4. List the `TLR` issues. For each of them:

    1. Get a list of all _mitigations_ linked to this risk with a `mitigates` relationship. Mitigation is defined as follows:

        1. If the mitigation is a functional requirement (`T`LF`R`), show it.

        2. If the mitigation is a development task (`LOOP`) or instruction for use (`IFU`), check to see if it is defined by one or more functional requirements (`TLFR`). If there is one or more functional requirement (`TLFR`), show those.

        3. Else, show the development task (`LOOP`) or instruction for use (`IFU`) instead.

### Insulin Fidelity

This sheet is a condensed version of the hazard analysis sheet for a subset of risks specifically related to insulin delivery fidelity. It lists each `TLR` risk, and summarizes the mitigating functional requirements (`TLFR`) and related development tasks (`LOOP`) and verification tests (`LOOP`).

### Open Defects

This sheet is a simple list of all open defects (=bugs) in the `LOOP` project, regardless of `fix_version`.

### Automated Tests

This sheet is a simple list of all automated tests reported by the automated builds. Unlike the other sheets, the data for this sheet is pulled from test reports stored in the AWS S3 bucket identified by the [tests.yml](config/inputs/tests.yml) configuration file.

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
