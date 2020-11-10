#!/usr/bin/env python3
"""
Copyright (c) 2020, Tidepool Project
All rights reserved.
"""
from doit.tools import title_with_actions

DOIT_CONFIG = {
    'default_tasks': [ 'excel' ],
    'continue': False,
}

def task_lint():
    """
    run lint on the source code
    """
    return {
        'actions': [ 'python3 -m pylint --jobs 8 ./**/*.py' ],
        'title': title_with_actions,
        'verbosity': 2,
    }

def task_excel():
    """
    generate Excel output
    """
    return {
        'actions': [ './report.py --excel' ],
        'title': title_with_actions,
        'verbosity': 2,
    }

def task_html():
    """
    generate HTML output
    """
    return {
        'actions': [ './report.py --html' ],
        'title': title_with_actions,
        'verbosity': 2,
    }

def task_d3js():
    """
    generate D3.js output
    """
    return {
        'actions': [ './report.py --d3js' ],
        'title': title_with_actions,
        'verbosity': 2,
    }

def task_all():
    """
    generate all outputs
    """
    return {
        'actions': None,
        'task_dep': [ 'excel', 'html', 'd3js' ],
        'title': title_with_actions,
        'verbosity': 2,
    }

def task_clobber():
    """
    clobber output and cache folders
    """
    return {
        'actions': [ 'rm -rv output/ cache/' ],
        'title': title_with_actions,
        'verbosity': 2,
    }
