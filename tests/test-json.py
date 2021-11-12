#!/usr/bin/env python3

import pytest
import json
import multiplex
import re

class TestJSON:

    # helper function to load json string from file
    def _load_json(self, filename):
        with open("tests/JSON/" + filename, "r") as file:
            return file.read().rstrip("\n")

    # fixture to load json object from file
    @pytest.fixture(scope="function")
    def load_json_file(self, request):
        return multiplex.load_json_file("tests/JSON/" + request.param)

    """Test if load_param_sets removes disabled params from global params"""
    @pytest.mark.parametrize("load_json_file",
                             [ "disabled-params-global.json" ], indirect=True)
    def test_disabled_global_params(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("enabled-global-expected.json")

        assert processed_json == expected_json

    """Test if load_param_sets removes disabled params from global params"""
    @pytest.mark.parametrize("load_json_file",
                             [ "disabled-params-sets.json" ], indirect=True)
    def test_disabled_sets_params(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("enabled-sets-expected.json")

        assert processed_json == expected_json

    """Test if multiplex_sets transforms multi-value sets into multiplexed
       single value ones"""
    @pytest.mark.parametrize("load_json_file",
                             [ "enabled-sets-expected.json" ], indirect=True)
    def test_multiplex_sets(self, load_json_file):
        multiplexed_json = multiplex.multiplex_sets(load_json_file)
        processed_json = json.dumps(multiplexed_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("single-value-sets-expected.json")

        assert processed_json == expected_json

    """Test if convert_vals transforms single-value vals key into val"""
    @pytest.mark.parametrize("load_json_file",
                             [ "single-value-sets-expected.json" ],
                             indirect=True)
    def test_convert_vals_into_val(self, load_json_file):
        final_json = multiplex.convert_vals(load_json_file)
        processed_json = json.dumps(final_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("final-expected.json")

        assert processed_json == expected_json

    """Test if load_param_sets handles multiple sets of params"""
    @pytest.mark.parametrize("load_json_file", [ "multi-params-sets.json" ],
                             indirect=True)
    def test_multi_params_sets(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("multi-sets-expected.json")

        assert processed_json == expected_json

    """Test if load_param_sets handles different ids"""
    @pytest.mark.parametrize("load_json_file", [ "params-ids.json" ],
                             indirect=True)
    def test_params_ids(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("expected-params-ids.json")

        assert processed_json == expected_json

    """Test if multiplex_sets handles multiple sets of multi-value params"""
    @pytest.mark.parametrize("load_json_file", [ "multi-sets-expected.json" ],
                             indirect=True)
    def test_multiplex_multi_sets(self, load_json_file):
        multiplexed_json = multiplex.multiplex_sets(load_json_file)
        processed_json = json.dumps(multiplexed_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("multiplexed-expected.json")

        assert processed_json == expected_json

    """Test if convert_vals replaces vals with val on multiplexed json"""
    @pytest.mark.parametrize("load_json_file", [ "multiplexed-expected.json" ],
                             indirect=True)
    def test_convert_vals(self, load_json_file):
        finalized_json = multiplex.convert_vals(load_json_file)
        for sets in finalized_json:
            for set in sets:
                assert 'vals' not in set
                assert 'val' in set

    """Test if dup params with different roles are not overrriden"""
    @pytest.mark.parametrize("load_json_file", [ "dup-param-diff-role.json" ],
                             indirect=True)
    def test_dup_param_diff_role(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        multiplexed_json = multiplex.multiplex_sets(combined_json)
        finalized_json = multiplex.convert_vals(multiplexed_json)
        processed_json = json.dumps(finalized_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("expected-dup-param-diff-role.json")

        assert processed_json == expected_json

    """Test if load_param_sets loads multiple sets from global params"""
    @pytest.mark.parametrize("load_json_file",
                             [ "include-global-multi.json" ], indirect=True)
    def test_multi_global_params(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("include-global-multi-expected.json")

        assert processed_json == expected_json

    """Test if load_param_sets loads single set from global params"""
    @pytest.mark.parametrize("load_json_file",
                             [ "include-global-single.json" ], indirect=True)
    def test_single_global_params(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("include-global-single-expected.json")

        assert processed_json == expected_json


