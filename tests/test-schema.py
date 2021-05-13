#!/bin/python3

import pytest

import json
import traceback
import os

from jsonschema import validate


def test_validate_schema():
    json_schema_file = "%s/../%s" % (os.path.dirname(os.path.abspath(__file__)), "schema.json")
    schema_fp = open(json_schema_file, 'r')
    try:
        json_obj = json.load(schema_fp)
    except:
        pytest.fail("Invalid schema.json")

    print(json_obj)
    schema_fp.close()
