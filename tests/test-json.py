#!/usr/bin/env python3

import pytest
import json
import multiplex
import re

class TestJSON:
    json_disabled_params_global="""
    {
        "global-options": [
            {
                "name": "common-params",
                "params": [
                    { "arg": "rw", "vals": [ "read", "write" ], "enabled": "no" }
                ]
            }
        ],
        "sets": [
            [
                { "include": "common-params" },
                { "arg": "ioengine", "vals": [ "sync" ], "enabled": "yes" }
            ]
        ]
    }
    """
    json_enabled_global_expected="""[[{"arg": "ioengine", "vals": ["sync"]}]]"""

    json_disabled_params_sets="""
    {
        "global-options": [
            {
                "name": "common-params",
                "params": [
                    { "arg": "rw", "vals": [ "read", "write" ], "enabled": "yes" }
                ]
            }
        ],
        "sets": [
            [
                { "include": "common-params" },
                { "arg": "ioengine", "vals": [ "sync" ], "enabled": "no" }
            ]
        ]
    }
    """

    # This is the output of handle_global_opts function and
    # the input for multiplex_sets function
    json_enabled_sets_expected="""[[{"arg": "rw", "vals": ["read", "write"]}]]"""

    json_single_value_sets_expected="""
    [[{"arg": "rw", "role": "client", "vals": ["read"]}],
    [{"arg": "rw", "role": "client", "vals": ["write"]}]]
    """

    json_final_expected="""
    [[{"arg": "rw", "role": "client", "val": "read"}],
    [{"arg": "rw", "role": "client", "val": "write"}]]
    """


    @pytest.fixture(scope="function")
    def load_json(self, request):
        return json.loads(request.param)


    """Test if handle_global_opts removes disabled params from global params"""
    @pytest.mark.parametrize("load_json", [ json_disabled_params_global ], indirect=True)
    def test_disabled_global_params(self, load_json):
        combined_json = multiplex.handle_global_opts(load_json)
        short_json = json.dumps(combined_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self.json_enabled_global_expected.replace("\n", "")

        assert short_json == expected_json


    """Test if hanlde_global_opts removes disabled params from global params"""
    @pytest.mark.parametrize("load_json", [ json_disabled_params_sets ], indirect=True)
    def test_disabled_sets_params(self, load_json):
        combined_json = multiplex.handle_global_opts(load_json)
        short_json = json.dumps(combined_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self.json_enabled_sets_expected.replace("\n", "")

        assert short_json == expected_json


    """Test if multiplex_sets transforms multi-value sets into multiplexed single value ones"""
    @pytest.mark.parametrize("load_json", [ json_enabled_sets_expected ], indirect=True)
    def test_multiplex_sets(self, load_json):
        multiplexed_json = multiplex.multiplex_sets(load_json)
        short_json = json.dumps(multiplexed_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self.json_single_value_sets_expected.replace("\n", "")

        assert short_json.replace(" ", "") == expected_json.replace(" ", "")


    """Test if convert_vals transforms single-value vals key into val"""
    @pytest.mark.parametrize("load_json", [ json_single_value_sets_expected ], indirect=True)
    def test_convert_vals_into_val(self, load_json):
        final_json = multiplex.convert_vals(load_json)
        short_json = json.dumps(final_json, sort_keys=True, indent=None).replace("\n", "")
        expected_json = self.json_final_expected.replace("\n", "")

        assert short_json.replace(" ", "") == expected_json.replace(" ", "")

