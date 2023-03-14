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

    @pytest.mark.parametrize("load_json_file", [ "schema-version-good.json" ], indirect=True)
    def test_validate_schema_version_good(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "schema.json")
        assert rt == True

    @pytest.mark.parametrize("load_json_file", [ "schema-version-bad.json" ], indirect=True)
    def test_validate_schema_version_bad(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "schema.json")
        assert rt == False

    """Test if load_param_sets handles invalid ids"""
    @pytest.mark.parametrize("load_json_file", [ "params-ids-invalid.json",
                                                 "params-ids-invalid-2.json",
                                                 "params-ids-invalid-3.json",
                                                 "params-ids-invalid-4.json",
                                                 "params-ids-invalid-5.json" ],
                             indirect=True)
    @pytest.mark.xfail(reason="invalid ids format")
    def test_params_ids_invalid(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "schema.json")
        assert rt is True
