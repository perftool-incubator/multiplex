#!/bin/python3

import pytest

import json
import traceback
import os

import multiplex

class TestSchema:

    @pytest.fixture(scope="function")
    def load_json_file(self, request):
        return multiplex.load_json_file(request.param)

    @pytest.fixture(scope="function")
    def load_json_inline(self):
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
                {
                    "include": "common-params",
                    "params": [
                        { "arg": "ioengine", "vals": [ "sync" ] }
                    ]
                }
            ]
        }
        """
        try:
            json_obj = json.loads(input_json)
        except:
            return None

        return json_obj

    def test_validate_schema(self, load_json_inline):
        rt = multiplex.validate_schema(load_json_inline, "schema.json")
        assert rt == True
