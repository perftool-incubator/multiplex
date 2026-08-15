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

    """Test that a requirements file with a valid 'repeatable' boolean
    passes req-schema.json validation"""
    @pytest.mark.parametrize("load_json_file", [ "requirements-repeatable.json" ], indirect=True)
    def test_validate_req_schema_repeatable_good(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "req-schema.json")
        assert rt == True

    """Test that a requirements file with a non-boolean 'repeatable' value
    fails req-schema.json validation"""
    @pytest.mark.parametrize("load_json_file", [ "requirements-repeatable-bad.json" ], indirect=True)
    def test_validate_req_schema_repeatable_bad(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "req-schema.json")
        assert rt == False

    """Test that a valid flat-mode array (arg/val[/enabled]) passes
    flat-schema.json validation"""
    @pytest.mark.parametrize("load_json_file", [ "flat-good.json" ], indirect=True)
    def test_validate_flat_schema_good(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "flat-schema.json")
        assert rt == True

    """Test that a flat-mode entry missing 'val' fails flat-schema.json
    validation"""
    @pytest.mark.parametrize("load_json_file", [ "flat-bad.json" ], indirect=True)
    def test_validate_flat_schema_bad(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "flat-schema.json")
        assert rt == False

    """Test that a flat-mode array with two byte-identical entries fails
    flat-schema.json validation, matching the uniqueItems strictness
    schema.json/req-schema.json already apply to their own arrays"""
    @pytest.mark.parametrize("load_json_file", [ "flat-duplicate.json" ], indirect=True)
    def test_validate_flat_schema_rejects_exact_duplicate(self, load_json_file):
        rt = multiplex.validate_schema(load_json_file, "flat-schema.json")
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
