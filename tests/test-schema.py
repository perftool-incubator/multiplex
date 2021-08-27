#!/bin/python3

import pytest

import json
import traceback
import os

import multiplex

class TestSchema:

    @pytest.fixture(scope="function")
    def load_json_file(self, request):
        return multiplex.load_json_file("tests/JSON/" + request.param)

    @pytest.mark.parametrize("load_json_file", [ "validate-schema-good.json" ], indirect=True)
    def test_validate_schema_good(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "schema.json")
        assert rt == True
