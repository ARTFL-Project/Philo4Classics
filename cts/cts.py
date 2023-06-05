#!/usr/bin/env python3

import os
from wsgiref.handlers import CGIHandler

import json

import sys
sys.path.append("..")
import custom_functions

from custom_functions import cts_results

try:
    from custom_functions import WebConfig
except ImportError:
    from philologic.runtime import WebConfig

def cts_wrapper(environ, start_response):
    config = WebConfig(os.path.abspath(os.path.dirname(__file__)).replace('reports', ''))
    headers = [('Content-type', 'text/xml; charset=UTF-8'),
               ("Access-Control-Allow-Origin", "*")]
    start_response('200 OK', headers)
    cts_config = json.load(open("data/cts.cfg"))
    cts_query = environ["QUERY_STRING"]
    cts_response = cts_results(cts_query, cts_config, config)
    return [cts_response.encode('utf-8')]

if __name__ == "__main__":
    CGIHandler().run(cts_wrapper)
