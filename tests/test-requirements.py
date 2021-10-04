#!/usr/bin/env python3

import pytest
import json
import re
import multiplex

class TestRequirements:

    requirements_json = "requirements-pass.json"
    req_presets_empty = "requirements-presets-empty-pass.json"
    req_single_escape = "requirements-single-escape-fail.json"

    """Common function to load requirements"""
    @pytest.fixture(scope="function")
    def load_req(self, request):
        req_json = multiplex.load_json_file("tests/JSON/"+ request.param)
        return req_json

    """Common function to validate param"""
    @pytest.fixture(scope="function")
    def validate_param(self, request):
        multiplex.log = multiplex.logging.getLogger()
        validated = multiplex.param_validated(next(iter(multiplex.validation_dict)), request.param)
        return validated

    """Test if requirements json file is successfully loaded"""
    @pytest.mark.parametrize("load_req", [ requirements_json ], indirect=True)
    def test_load_requirements(self, load_req):

        assert load_req is not None
        assert 'presets' in load_req

    """Test if validation dict is successfully created"""
    @pytest.mark.parametrize("load_req", [ requirements_json ], indirect=True)
    def test_create_validation_dict(self, load_req):
        multiplex.create_validation_dict(load_req)

        assert multiplex.validation_dict is not {}
        assert 'bs' in multiplex.validation_dict.keys()

    """Test if presets dict is successfully loaded"""
    @pytest.mark.parametrize("load_req", [ requirements_json ], indirect=True)
    def test_load_presets(self, load_req):
        assert multiplex.presets_dict == {}
        multiplex.load_presets(load_req)
        print(multiplex.presets_dict)
        assert 'essentials' in multiplex.presets_dict
        param = next((item for item in multiplex.presets_dict["essentials"] if item["arg"] == "duration"), False)
        assert param["vals"] == ["60"]
        param = next((item for item in multiplex.presets_dict["defaults"] if item["arg"] == "bs"), False)
        assert param["vals"] == ["16K"]
        param = next((item for item in multiplex.presets_dict["sequential-read"] if item["arg"] == "bs"), False)
        assert param["vals"] == ["4K"]

    """Test if validation regex w/ single escape fails"""
    @pytest.mark.parametrize("load_req", [ req_single_escape ], indirect=True)
    @pytest.mark.xfail(reason="single escape raises an exception")
    def test_create_validation_dict(self, load_req):
        assert multiplex.load_json_file(load_req) is None

    """Test if validation dict has empty presets (which is ok)"""
    @pytest.mark.parametrize("load_req", [ req_presets_empty ], indirect=True)
    def test_empty_presets(self, load_req):
        multiplex.create_validation_dict(load_req)

        assert multiplex.validation_dict is not {}
        assert load_req['presets'] == {}

    """Test if requirements w/ empty presets validates schema (ok)"""
    @pytest.mark.parametrize("load_req", [ req_presets_empty ], indirect=True)
    def test_validate_schema_empty_presets(self, load_req):
        valid_requirements = multiplex.validate_schema(load_req, "req-schema.json")

        assert valid_requirements is True

    """Test invalid vals"""
    @pytest.mark.parametrize("validate_param", [ "bar", "012", "60s", "0", "-300", "0.5" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "duration": "^[1-9]+[0-9]*$" } ])
    def test_invalid_val(self, validate_param, val_dict):
        multiplex.validation_dict = val_dict
        assert validate_param is False

    """Test valid vals"""
    @pytest.mark.parametrize("validate_param", [ "60", "1", "3600" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "duration": "^[1-9]+[0-9]*$" } ])
    def test_valid_val(self, validate_param, val_dict):
        multiplex.validation_dict = val_dict
        assert validate_param is True

    """Test invalid vals w/ unit"""
    @pytest.mark.parametrize("validate_param", [ "0512B", "-64B", "0B", "J" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "frame-size": "^(([1-9][0-9]*\\.?[0-9]*)|(0?\\.[0-9]+)).*[BKMG]?" } ])
    def test_invalid_val_unit(self, validate_param, val_dict):
        multiplex.validation_dict = val_dict
        assert validate_param is False

    """Test valid vals w/ unit"""
    @pytest.mark.parametrize("validate_param", [ "64B", "1k", "9216B", "0.1M", "0.001G" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "duration": "^(([1-9][0-9]*\\.?[0-9]*)|(0?\\.[0-9]+)).*[BKMG]?" } ])
    def test_valid_val_unit(self, validate_param, val_dict):
        multiplex.validation_dict = val_dict
        assert validate_param is True

    """Test missing validation (there is no validation for mtu param)"""
    def test_missing_validations(self, caplog):
        multiplex.validation_dict = { "frame-size": "^(([1-9][0-9]*\\.?[0-9]*)|(0?\\.[0-9]+)).*[BKMG]?" }
        validated = multiplex.param_validated("mtu", "1500")
        assert validated is False
        assert "Validation for param='mtu' not found in the requirements file." in caplog.text

    """Test validate_param with empty/missing requirements file (empty validation_dict)"""
    def test_validate_param_no_requirements(self):
        multiplex.validation_dict = {}
        validated = multiplex.param_validated("mtu", "1500")
        assert validated is True
