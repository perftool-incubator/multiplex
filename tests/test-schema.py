#!/bin/python3

import pytest

import json
import traceback
import os

from jsonschema import validate


class TestSchema:

    @pytest.fixture
    def load_schema(self):
        json_schema_file = "%s/../%s" % (os.path.dirname(os.path.abspath(__file__)), "schema.json")
        schema_fp = open(json_schema_file, 'r')
        try:
            json_obj = json.load(schema_fp)
            schema_fp.close()
        except:
            return None

        return json_obj


    @pytest.fixture
    def load_json(self):
        input_json="""
        {
            "global-options": [
                {
                    "name": "common-params",
                    "params": [
                        { "arg": "bs", "vals": [ "4k", "8k" ], "role": "client" },
                        { "arg": "rw", "vals": [ "read", "write" ] }
                    ]
                }
            ],
            "sets": [
                [
                    { "include": "common-params" },
                    { "arg": "ioengine", "vals": [ "sync" ] }
                ]
            ]
        }
        """
        try:
            json_obj = json.loads(input_json)
        except:
            return None

        return json_obj


    def test_validate_schema(self, load_schema):
        assert load_schema != None


    def test_validate_json(self, load_schema, load_json):
        try:
            validate(instance = load_json, schema = load_schema)
        except:
            pytest.fail("Invalid JSON")
