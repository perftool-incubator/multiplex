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

    """Test if load_param_sets removes disabled params from global a 2nd time"""
    @pytest.mark.parametrize("load_json_file",
                             [ "disabled-params-global-2nd.json" ], indirect=True)
    def test_disabled_global_params_2nd(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("enabled-global-expected-2nd.json")

        assert processed_json == expected_json

    """Test if load_param_sets removes disabled params from params sets"""
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

    """Test that two of a set's own params sharing the same arg (and role/id)
    both survive rather than the second silently overwriting the first --
    e.g. tool-kernel's repeatable sysfs-trace-setup/-cleanup commands,
    declared repeatable in the requirements file"""
    @pytest.mark.parametrize("load_json_file", [ "dup-param-same-set.json" ],
                             indirect=True)
    def test_dup_param_same_set_both_survive(self, load_json_file):
        multiplex.repeatable_args = { "sysfs-trace-setup": True }
        combined_json = multiplex.load_param_sets(load_json_file)
        multiplexed_json = multiplex.multiplex_sets(combined_json)
        finalized_json = multiplex.convert_vals(multiplexed_json)
        processed_json = json.dumps(finalized_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("expected-dup-param-same-set.json")

        assert processed_json == expected_json

    """Test that when 'include' is combined with two of the set's own
    same-arg params on a repeatable arg, all three entries (the included
    default plus both own params) survive as a union -- a repeatable arg
    is never collapsed or overridden, regardless of where each occurrence
    came from"""
    @pytest.mark.parametrize("load_json_file",
                             [ "dup-param-same-set-with-include.json" ],
                             indirect=True)
    def test_dup_param_same_set_with_include(self, load_json_file):
        multiplex.repeatable_args = { "sysfs-trace-setup": True }
        combined_json = multiplex.load_param_sets(load_json_file)
        multiplexed_json = multiplex.multiplex_sets(combined_json)
        finalized_json = multiplex.convert_vals(multiplexed_json)
        processed_json = json.dumps(finalized_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("expected-dup-param-same-set-with-include.json")

        assert processed_json == expected_json

    """Test that a repeatable arg arriving via both 'include' and the
    set's own 'params' with a byte-for-byte identical value (same arg,
    vals, role, and id) is deduped to one occurrence rather than running
    the same command twice -- exercises exact_duplicate_exists()'s actual
    skip branch, which the other repeatable fixtures above never trigger
    since they only use distinct values per occurrence"""
    @pytest.mark.parametrize("load_json_file",
                             [ "dup-param-exact-duplicate.json" ],
                             indirect=True)
    def test_dup_param_exact_duplicate_collapses_to_one(self, load_json_file):
        multiplex.repeatable_args = { "sysfs-trace-setup": True }
        combined_json = multiplex.load_param_sets(load_json_file)
        multiplexed_json = multiplex.multiplex_sets(combined_json)
        finalized_json = multiplex.convert_vals(multiplexed_json)
        processed_json = json.dumps(finalized_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("expected-dup-param-exact-duplicate.json")

        assert processed_json == expected_json

    """Test that a set's own param still overrides a same-arg, same-role
    param brought in via 'include' -- the override mechanism the dup-param
    fix above must not break"""
    @pytest.mark.parametrize("load_json_file",
                             [ "override-included-param-same-role.json" ],
                             indirect=True)
    def test_override_included_param_same_role(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        multiplexed_json = multiplex.multiplex_sets(combined_json)
        finalized_json = multiplex.convert_vals(multiplexed_json)
        processed_json = json.dumps(finalized_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("expected-override-included-param-same-role.json")

        assert processed_json == expected_json

    """Test that two included sources (two global-options groups here)
    sharing a same-arg/role/id identity log a warning -- a likely
    authoring mistake, matching the diagnostic 'defaults'/'essentials'
    already provide for the analogous conflict -- while the first one
    still wins (existing include semantics, unchanged)"""
    def test_include_conflict_between_two_groups_warns(self, caplog):
        sets_block = {
            "global-options": [
                { "name": "g1", "params": [ { "arg": "bs", "vals": [ "4K" ] } ] },
                { "name": "g2", "params": [ { "arg": "bs", "vals": [ "8K" ] } ] },
            ],
            "sets": [ { "include": [ "g1", "g2" ] } ],
        }
        combined_json = multiplex.load_param_sets(sets_block)

        assert combined_json == [ [ { "arg": "bs", "vals": [ "4K" ] } ] ]
        assert "Multiple included params found" in caplog.text

    """Test the same conflict shape as above, but as an accidental
    duplicate within a SINGLE global-options group's own params list
    (rather than across two groups) -- include's own first-wins
    semantics (deliberate and pre-existing, unlike own-params/defaults/
    essentials' last-wins) apply identically regardless of whether the
    duplicate spans one source or two, and still warns"""
    def test_include_conflict_within_one_group_warns(self, caplog):
        sets_block = {
            "global-options": [
                { "name": "g1", "params": [
                    { "arg": "bs", "vals": [ "4K" ] },
                    { "arg": "bs", "vals": [ "8K" ] },
                ] },
            ],
            "sets": [ { "include": "g1" } ],
        }
        combined_json = multiplex.load_param_sets(sets_block)

        assert combined_json == [ [ { "arg": "bs", "vals": [ "4K" ] } ] ]
        assert "Multiple included params found" in caplog.text

    """Test that a set's own param overriding an included value does NOT
    warn -- that's the normal, documented override contract, not a
    conflict between two included sources"""
    def test_own_param_overriding_include_does_not_warn(self, caplog):
        sets_block = {
            "global-options": [
                { "name": "g1", "params": [ { "arg": "bs", "vals": [ "4K" ] } ] },
            ],
            "sets": [ { "include": "g1", "params": [ { "arg": "bs", "vals": [ "8K" ] } ] } ],
        }
        combined_json = multiplex.load_param_sets(sets_block)

        assert combined_json == [ [ { "arg": "bs", "vals": [ "8K" ] } ] ]
        assert "Multiple included params found" not in caplog.text

    """Test that two same-arg params within a set's own 'params' list log
    a warning -- the single most likely place for a copy-paste mistake,
    now getting the same diagnostic as the identical conflict shape in
    defaults/essentials/include"""
    def test_own_params_conflict_warns(self, caplog):
        sets_block = {
            "global-options": [],
            "sets": [ { "params": [
                { "arg": "bs", "vals": [ "4k" ] },
                { "arg": "bs", "vals": [ "64k" ] },
            ] } ],
        }
        combined_json = multiplex.load_param_sets(sets_block)

        assert combined_json == [ [ { "arg": "bs", "vals": [ "64k" ] } ] ]
        assert "Multiple params found" in caplog.text

    """Test that duplicate same-arg params still collapse to the last one
    when the arg isn't declared repeatable -- the protective historical
    default for args where a duplicate is more likely to be a mistake than
    an intentional repeat"""
    @pytest.mark.parametrize("load_json_file",
                             [ "dup-param-not-repeatable.json" ],
                             indirect=True)
    def test_dup_param_not_repeatable_still_collapses(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        multiplexed_json = multiplex.multiplex_sets(combined_json)
        finalized_json = multiplex.convert_vals(multiplexed_json)
        processed_json = json.dumps(finalized_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("expected-dup-param-not-repeatable.json")

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

    """Test if load_param_sets handles enabled=yes set"""
    @pytest.mark.parametrize("load_json_file", [ "multi-params-sets-enabled.json" ],
                             indirect=True)
    def test_multi_params_sets_enabled(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("multi-sets-expected.json")

        assert processed_json == expected_json

    """Test if load_param_sets handles enabled=no set"""
    @pytest.mark.parametrize("load_json_file", [ "multi-params-sets-disabled.json" ],
                             indirect=True)
    def test_multi_params_sets_disabled(self, load_json_file):
        combined_json = multiplex.load_param_sets(load_json_file)
        processed_json = json.dumps(combined_json, sort_keys=True, indent=4,
                                    separators=(',',': '))
        expected_json = self._load_json("multi-sets-expected-disabled.json")

        assert processed_json == expected_json
