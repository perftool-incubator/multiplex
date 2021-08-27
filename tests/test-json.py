#!/usr/bin/env python3

import pytest
import json
import multiplex
import re

class TestJSON:

    # helper function to load json string from file
    def _load_json(self, filename):
        return open("tests/JSON/" + filename).read()

    # fixture to load json object from file
    @pytest.fixture(scope="function")
    def load_json_file(self, request):
        return multiplex.load_json_file("tests/JSON/" + request.param)

    """Test if load_param_sets removes disabled params from global params"""
    @pytest.mark.parametrize("load_json_file", [ "disabled-params-global.json" ], indirect=True)
    def test_disabled_global_params(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        short_json = json.dumps(combined_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self._load_json("enabled-global-expected.json").replace("\n", "")

        assert short_json == expected_json


    """Test if load_param_sets removes disabled params from global params"""
    @pytest.mark.parametrize("load_json_file", [ "disabled-params-sets.json" ], indirect=True)
    def test_disabled_sets_params(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        short_json = json.dumps(combined_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self._load_json("enabled-sets-expected.json").replace("\n", "")

        assert short_json == expected_json


    """Test if multiplex_sets transforms multi-value sets into multiplexed single value ones"""
    @pytest.mark.parametrize("load_json_file", [ "enabled-sets-expected.json" ], indirect=True)
    def test_multiplex_sets(self, load_json_file):
        global validation_dict
        multiplexed_json = multiplex.multiplex_sets(load_json_file)
        short_json = json.dumps(multiplexed_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self._load_json("single-value-sets-expected.json").replace("\n", "")

        assert short_json.replace(" ", "") == expected_json.replace(" ", "")


    """Test if convert_vals transforms single-value vals key into val"""
    @pytest.mark.parametrize("load_json_file", [ "single-value-sets-expected.json" ], indirect=True)
    def test_convert_vals_into_val(self, load_json_file):
        final_json = multiplex.convert_vals(load_json_file)
        short_json = json.dumps(final_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self._load_json("final-expected.json").replace("\n", "")

        assert short_json.replace(" ", "") == expected_json.replace(" ", "")

    """Test if load_param_sets handles multiple sets of params"""
    @pytest.mark.parametrize("load_json_file", [ "multi-params-sets.json" ], indirect=True)
    def test_multi_params_sets(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        short_json = json.dumps(combined_json, sort_keys=True, indent=None).replace("\n", "")
        short_json = short_json.replace(" ", "")
        expected_json = self._load_json("multi-sets-expected.json").replace("\n", "")
        expected_json = expected_json.replace(" ", "")

        assert short_json == expected_json

    """Test if multiplex_sets handles multiple sets of multi-value params"""
    @pytest.mark.parametrize("load_json_file", [ "multi-sets-expected.json" ], indirect=True)
    def test_multiplex_multi_sets(self, load_json_file):
        global validation_dict
        multiplexed_json = multiplex.multiplex_sets(load_json_file)
        short_json = json.dumps(multiplexed_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self._load_json("multiplexed-expected.json").replace("\n", "")
        short_json = short_json.replace(" ", "")
        expected_json = expected_json.replace(" ", "")

        assert short_json == expected_json

    """Test if convert_vals replaces vals with val on multiplexed json"""
    @pytest.mark.parametrize("load_json_file", [ "multiplexed-expected.json" ], indirect=True)
    def test_convert_vals(self, load_json_file):
        finalized_json = multiplex.convert_vals(load_json_file)
        for sets in finalized_json:
            for set in sets:
                assert 'vals' not in set
                assert 'val' in set
