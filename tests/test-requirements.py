#!/usr/bin/env python3

import pytest
import json
import re
import multiplex

class TestRequirements:

    requirements_json = "requirements-pass.json"
    req_presets_def_ess_empty = "requirements-presets-def-ess-empty.json"
    req_presets_empty = "requirements-presets-empty-pass.json"
    req_single_escape = "requirements-single-escape-fail.json"

    json_missing_sets_and_globals = "missing-params-sets-and-global.json"
    json_missing_sets_empty_globals = "missing-params-sets-empty-global.json"
    json_empty_sets_and_globals = "empty-params-sets-and-global.json"
    json_empty_sets_missing_globals = "empty-params-sets-missing-global.json"

    # helper function to load json string from file
    def _load_json(self, filename):
        with open("tests/JSON/" + filename, "r") as file:
            return file.read().rstrip("\n")

    """Common function to load json"""
    @pytest.fixture(scope="function")
    def load_json(self, request):
        load_json = multiplex.load_json_file("tests/JSON/"+ request.param)
        return load_json

    """Common function to load requirements"""
    @pytest.fixture(scope="function")
    def load_req(self, request):
        req_json = multiplex.load_json_file("tests/JSON/"+ request.param)
        return req_json

    """Common function to validate param. Sets validation_dict from
    val_dict itself (rather than relying on the test body's own
    'multiplex.validation_dict = val_dict' line, which runs too late --
    after this fixture has already computed and returned its result).
    This was previously masked by validation_dict happening to still
    hold a compatible leftover value from whichever test ran immediately
    before it in file order -- an order-dependent accident, not a real
    guarantee, exposed once conftest.py started properly resetting
    validation_dict between tests."""
    @pytest.fixture(scope="function")
    def validate_param(self, request, val_dict):
        multiplex.log = multiplex.logging.getLogger()
        multiplex.validation_dict = val_dict
        validated = multiplex.param_validated(next(iter(val_dict)), request.param)
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

        assert multiplex.validation_dict != {}
        assert 'bs' in multiplex.validation_dict.keys()

    """Test that a validation group's 'repeatable' flag flows through to
    repeatable_args, scoped only to that group's own args"""
    @pytest.mark.parametrize("load_req", [ "requirements-repeatable.json" ],
                             indirect=True)
    def test_create_validation_dict_repeatable(self, load_req):
        multiplex.create_validation_dict(load_req)

        assert multiplex.is_repeatable("sysfs-trace-setup") is True
        assert multiplex.is_repeatable("sysfs-trace-cleanup") is True
        assert multiplex.is_repeatable("record-opts") is False

    """Test the full create_validation_dict() -> repeatable_args ->
    load_param_sets() chain end-to-end, driven by a real requirements
    file, rather than hand-assigning multiplex.repeatable_args as the
    other dup-param tests in test-json.py do -- so a regression in how
    create_validation_dict() actually populates repeatable_args (e.g. a
    keying or scoping change) would be caught here even if those other
    tests kept passing"""
    @pytest.mark.parametrize("load_req", [ "requirements-repeatable.json" ],
                             indirect=True)
    def test_create_validation_dict_repeatable_flows_to_load_param_sets(self, load_req):
        multiplex.create_validation_dict(load_req)

        json_obj = multiplex.load_json_file("tests/JSON/dup-param-same-set.json")
        combined_json = multiplex.load_param_sets(json_obj)

        setups = [ p for p in combined_json[0] if p["arg"] == "sysfs-trace-setup" ]
        assert len(setups) == 2

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
        assert param == False
        param = next((item for item in multiplex.presets_dict["sequential-read"] if item["arg"] == "bs"), False)
        assert param["vals"] == ["4K"]

    """Test that a requirements file with invalid JSON (an unescaped
    single backslash) fails to load gracefully -- the load_req fixture
    itself calls load_json_file() on the invalid file, which catches the
    real JSONDecodeError and returns None rather than raising. The xfail
    marker this test carried previously only "passed" via a masking
    NameError (log was undefined at module scope); asserting on load_req
    directly (rather than redundantly re-calling load_json_file() on the
    already-None result, which only exercises an unrelated TypeError from
    open(None, 'r')) actually verifies the parse failure this test is
    named for."""
    @pytest.mark.parametrize("load_req", [ req_single_escape ], indirect=True)
    def test_create_validation_dict_single_escape(self, load_req):
        assert load_req is None

    """Test if validation dict has empty presets (which is ok)"""
    @pytest.mark.parametrize("load_req", [ req_presets_empty ], indirect=True)
    def test_empty_presets(self, load_req):
        multiplex.create_validation_dict(load_req)

        assert multiplex.validation_dict != {}
        assert load_req['presets'] == {}

    """Test if requirements w/ empty presets validates schema (ok)"""
    @pytest.mark.parametrize("load_req", [ req_presets_empty ], indirect=True)
    def test_validate_schema_empty_presets(self, load_req):
        valid_requirements = multiplex.validate_schema(load_req, "req-schema.json")

        assert valid_requirements is True

    """Test invalid vals"""
    @pytest.mark.parametrize("validate_param", [ "bar", "012", "60s", "0", "-300", "0.5" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "duration": "^[1-9]+[0-9]*$" } ])
    def test_invalid_val(self, validate_param):
        assert validate_param is False

    """Test valid vals"""
    @pytest.mark.parametrize("validate_param", [ "60", "1", "3600" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "duration": "^[1-9]+[0-9]*$" } ])
    def test_valid_val(self, validate_param):
        assert validate_param is True

    """Test invalid vals w/ unit"""
    @pytest.mark.parametrize("validate_param", [ "0512B", "-64B", "0B", "J" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "frame-size": "^(([1-9][0-9]*\\.?[0-9]*)|(0?\\.[0-9]+)).*[BKMG]?" } ])
    def test_invalid_val_unit(self, validate_param):
        assert validate_param is False

    """Test valid vals w/ unit"""
    @pytest.mark.parametrize("validate_param", [ "64B", "1k", "9216B", "0.1M", "0.001G" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "duration": "^(([1-9][0-9]*\\.?[0-9]*)|(0?\\.[0-9]+)).*[BKMG]?" } ])
    def test_valid_val_unit(self, validate_param):
        assert validate_param is True

    """Test invalid vals array"""
    @pytest.mark.parametrize("validate_param", [ "0023", "abc" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "param2": ["^[1-9]+[0-9]*$", "^[A-Z]*$"] } ])
    def test_invalid_val_array(self, validate_param):
        assert validate_param is False

    """Test valid vals array"""
    @pytest.mark.parametrize("validate_param", [ "60", "ABC" ], indirect=True)
    @pytest.mark.parametrize("val_dict", [ { "param1": ["^[1-9]+[0-9]*$", "^[A-Z]*$"] } ])
    def test_valid_val_array(self, validate_param):
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

    """Test presets overrides (defaults and essentials)"""
    @pytest.mark.parametrize("load_req", [ requirements_json ], indirect=True)
    def test_override_presets(self, load_req):
        multiplex.load_presets(load_req)
        json1 = multiplex.load_json_file("tests/JSON/multi-params-sets.json")
        json2 = multiplex.load_param_sets(json1)
        json3 = multiplex.override_presets(json2)
        processed = json.dumps(json3, indent=4, sort_keys=True,
                                separators=(',',': '))
        expected = self._load_json("expected-override-presets.json")
        assert processed == expected

    """Test that an essential for a repeatable arg is unioned with the
    set's own values (added only if not already present) rather than
    replacing them -- essentials guarantee presence, not exclusivity, and
    removal only makes sense for an arg that can't legitimately repeat"""
    def test_override_presets_essentials_union_for_repeatable_arg(self, reset_presets_dict):
        multiplex.repeatable_args = { "foo": True }
        multiplex.presets_dict = {
            "essentials": [
                { "arg": "foo", "vals": [ "bar" ] },
                { "arg": "foo", "vals": [ "baz" ] },
            ]
        }
        json_obj = [[ { "arg": "foo", "vals": [ "zorg" ] } ]]
        result = multiplex.override_presets(json_obj)

        vals = sorted(p["vals"][0] for p in result[0])
        assert vals == ["bar", "baz", "zorg"]

    """Test that a repeatable arg's occurrence with more than one value is
    rejected outright -- multiple distinct single-valued occurrences are
    supported and tested elsewhere, but sweeping one occurrence's own
    values has no defined meaning yet and must fail loudly rather than
    silently cross-multiplying against other occurrences"""
    def test_merge_repeatable_param_rejects_multi_valued_occurrence(self, reset_presets_dict):
        multiplex.repeatable_args = { "foo": True }
        param_set = []

        with pytest.raises(SystemExit):
            multiplex.merge_repeatable_param(
                { "arg": "foo", "vals": [ "bar", "baz" ] }, param_set
            )

    """Test that multiple single-valued occurrences of a repeatable arg
    are unaffected by the multi-valued guard above -- only an individual
    occurrence's own vals length matters, not how many occurrences exist"""
    def test_merge_repeatable_param_allows_multiple_single_valued_occurrences(self, reset_presets_dict):
        multiplex.repeatable_args = { "foo": True }
        param_set = []

        multiplex.merge_repeatable_param({ "arg": "foo", "vals": [ "bar" ] }, param_set)
        multiplex.merge_repeatable_param({ "arg": "foo", "vals": [ "baz" ] }, param_set)

        vals = sorted(p["vals"][0] for p in param_set)
        assert vals == ["bar", "baz"]

    """Test that an essential applies independently to every set that
    needs it, not just the first one processed -- override_presets() must
    not destructively consume presets_dict['essentials'] as it goes"""
    def test_override_presets_essentials_apply_to_every_set(self, reset_presets_dict):
        multiplex.presets_dict = {
            "essentials": [ { "arg": "bs", "vals": [ "1K" ] } ]
        }
        json_obj = [
            [ { "arg": "bs", "vals": [ "32K" ] } ],
            [ { "arg": "bs", "vals": [ "64K" ] } ],
        ]
        result = multiplex.override_presets(json_obj)

        assert result[0] == [ { "arg": "bs", "vals": [ "1K" ] } ]
        assert result[1] == [ { "arg": "bs", "vals": [ "1K" ] } ]

    """Test that a 'defaults' preset with an accidental same-arg
    duplicate collapses to the last value, matching the same
    single-occurrence contract essentials/include/own-params already
    have -- 'defaults' used to be applied as a verbatim deepcopy with no
    merge logic at all, so a duplicate here would silently produce two
    conflicting values for one arg"""
    def test_override_presets_defaults_collapses_duplicate_arg(self, reset_presets_dict):
        multiplex.presets_dict = {
            "defaults": [
                { "arg": "iterations", "vals": [ "1" ] },
                { "arg": "iterations", "vals": [ "2" ] },
            ]
        }
        result = multiplex.override_presets([[]])

        assert result[0] == [ { "arg": "iterations", "vals": [ "2" ] } ]

    """Test that a duplicate-arg conflict in 'defaults' is logged, once
    per run rather than once per target set -- matching the same
    diagnostic essentials already provide for the analogous case"""
    def test_override_presets_defaults_conflict_warns_once(self, reset_presets_dict, caplog):
        multiplex.presets_dict = {
            "defaults": [
                { "arg": "iterations", "vals": [ "1" ] },
                { "arg": "iterations", "vals": [ "2" ] },
            ]
        }
        multiplex.override_presets([[], []])

        warnings = [r for r in caplog.records if "Multiple defaults found" in r.message]
        assert len(warnings) == 1

    """Test that a disabled default cannot claim an (arg, role, id)
    identity and erase a later, actually-enabled default from applying --
    mirrors the same essentials fix, since 'defaults' now goes through
    the same merge_param_own()-based replace logic"""
    def test_override_presets_defaults_disabled_does_not_block_conflict(self, reset_presets_dict):
        multiplex.presets_dict = {
            "defaults": [
                { "arg": "iterations", "vals": [ "1" ] },
                { "arg": "iterations", "vals": [ "2" ], "enabled": "no" },
            ]
        }
        result = multiplex.override_presets([[]])

        assert result[0] == [ { "arg": "iterations", "vals": [ "1" ] } ]

    """Test that a disabled default doesn't trigger a false duplicate-
    conflict warning against the one default that's actually active"""
    def test_override_presets_defaults_disabled_does_not_false_warn(self, reset_presets_dict, caplog):
        multiplex.presets_dict = {
            "defaults": [
                { "arg": "iterations", "vals": [ "1" ], "enabled": "no" },
                { "arg": "iterations", "vals": [ "2" ] },
            ]
        }
        multiplex.override_presets([[]])

        warnings = [r for r in caplog.records if "Multiple defaults found" in r.message]
        assert len(warnings) == 0

    """Test that when two non-repeatable essentials share the same
    (arg, role, id), the last one applies -- matching this file's
    established last-group-wins convention (validation_dict/convert_dict/
    transform_dict/repeatable_args) rather than a direction unique to
    essentials. A warning is still logged so the requirements-file author
    knows the conflict happened."""
    def test_override_presets_essentials_last_wins_on_conflict(self, reset_presets_dict):
        multiplex.presets_dict = {
            "essentials": [
                { "arg": "foo", "vals": [ "first" ] },
                { "arg": "foo", "vals": [ "second" ] },
            ]
        }
        json_obj = [[ { "arg": "foo", "vals": [ "own" ] } ]]
        result = multiplex.override_presets(json_obj)

        assert result[0] == [ { "arg": "foo", "vals": [ "second" ] } ]

    """Test that an essentials conflict is logged once per run rather than
    once per target set -- the conflict is a static property of the
    requirements file's own essentials list, not of any particular set"""
    def test_override_presets_essentials_conflict_warns_once(self, reset_presets_dict, caplog):
        multiplex.presets_dict = {
            "essentials": [
                { "arg": "foo", "vals": [ "first" ] },
                { "arg": "foo", "vals": [ "second" ] },
            ]
        }
        json_obj = [[ { "arg": "bar", "vals": [ "1" ] } ], [ { "arg": "baz", "vals": [ "2" ] } ]]
        multiplex.override_presets(json_obj)

        warnings = [r for r in caplog.records if "Multiple essentials found" in r.message]
        assert len(warnings) == 1

    """Test that a disabled essential cannot claim an (arg, role, id)
    identity and block a later, actually-enabled essential from applying
    -- a disabled essential never reaches the target set at all, so it
    must not participate in conflict resolution for that identity"""
    def test_override_presets_essentials_disabled_does_not_block_conflict(self, reset_presets_dict):
        multiplex.presets_dict = {
            "essentials": [
                { "arg": "iterations", "vals": [ "1" ], "enabled": "no" },
                { "arg": "iterations", "vals": [ "3" ] },
            ]
        }
        json_obj = [[ { "arg": "foo", "vals": [ "bar" ] } ]]
        result = multiplex.override_presets(json_obj)

        assert result[0] == [
            { "arg": "foo", "vals": [ "bar" ] },
            { "arg": "iterations", "vals": [ "3" ] },
        ]

    """Test that a disabled essential doesn't trigger a false duplicate-
    conflict warning against the one essential that's actually active"""
    def test_override_presets_essentials_disabled_does_not_false_warn(self, reset_presets_dict, caplog):
        multiplex.presets_dict = {
            "essentials": [
                { "arg": "iterations", "vals": [ "1" ], "enabled": "no" },
                { "arg": "iterations", "vals": [ "3" ] },
            ]
        }
        multiplex.override_presets([[ { "arg": "foo", "vals": [ "bar" ] } ]])

        warnings = [r for r in caplog.records if "Multiple essentials found" in r.message]
        assert len(warnings) == 0

    """Test that two non-repeatable essentials sharing an arg but scoped
    to different roles both apply independently -- the conflict
    de-duplication above must be scoped by (arg, role, id), not arg alone,
    or a legitimately different-role essential would be wrongly skipped"""
    def test_override_presets_essentials_conflict_dedup_is_role_scoped(self, reset_presets_dict):
        multiplex.presets_dict = {
            "essentials": [
                { "arg": "bs", "vals": [ "4k" ], "role": "server" },
                { "arg": "bs", "vals": [ "8k" ], "role": "client" },
            ]
        }
        json_obj = [[ { "arg": "bs", "vals": [ "64k" ], "role": "client" } ]]
        result = multiplex.override_presets(json_obj)

        by_role = { p["role"]: p["vals"][0] for p in result[0] }
        assert by_role == { "server": "4k", "client": "8k" }

    """Test include named presets"""
    @pytest.mark.parametrize("load_req", [ requirements_json ], indirect=True)
    def test_include_preset(self, load_req):
        multiplex.load_presets(load_req)
        json1 = multiplex.load_json_file("tests/JSON/multi-params-sets-include-preset.json")
        json2 = multiplex.load_param_sets(json1)
        json3 = multiplex.override_presets(json2)
        processed = json.dumps(json3, indent=4, sort_keys=True,
                                separators=(',',': '))
        expected = self._load_json("expected-include-preset.json")
        assert processed == expected

    """Test include named presets w/ empty default/essentials"""
    @pytest.mark.parametrize("load_req", [ req_presets_def_ess_empty ], indirect=True)
    def test_presets_def_ess_empty(self, load_req):
        multiplex.presets_dict = {}
        multiplex.load_presets(load_req)
        j1 = multiplex.load_json_file("tests/JSON/multi-params-sets-include-preset.json")
        j2 = multiplex.load_param_sets(j1)
        j3 = multiplex.override_presets(j2)
        processed = json.dumps(j3, indent=4, sort_keys=True,
                                separators=(',',': '))
        expected = self._load_json("expected-include-preset-def-ess-empty.json")
        assert processed == expected

    """Test missing/empty set and global, no presets"""
    @pytest.mark.parametrize("load_json", [ json_missing_sets_and_globals,
                json_missing_sets_empty_globals, json_empty_sets_and_globals,
                json_empty_sets_missing_globals ], indirect=True)
    def test_missing_params_no_presets(self, load_json, caplog):
        json_req = self._load_json("multi-params-sets-include-preset.json")
        multiplex.load_presets(json_req)
        json1 = multiplex.load_param_sets(load_json)
        json2 = multiplex.override_presets(json1)
        assert "An empty param set has been found" in caplog.text
        assert json2 == None

    """Test missing/empty set and global, w/ defaults/essentials presets"""
    @pytest.mark.parametrize("load_json", [ json_missing_sets_and_globals,
                json_missing_sets_empty_globals, json_empty_sets_and_globals,
                json_empty_sets_missing_globals ], indirect=True)
    def test_missing_params_override_presets(self, load_json):
        multiplex.presets_dict = {}
        json_req = multiplex.load_json_file("tests/JSON/requirements-pass.json")
        multiplex.load_presets(json_req)
        json1 = multiplex.load_param_sets(load_json)
        json2 = multiplex.override_presets(json1)
        processed = json.dumps(json2, indent=4, sort_keys=True,
                                separators=(',',': '))
        expected = self._load_json("expected-presets-override-missing-params.json")
        assert processed == expected

    """Test (single) val convert K-to-None"""
    def test_convert_single(self):
        multiplex.convert_dict = { "size": { "": { "": "1", "B": "1", "K": "1024", "M": "1024*1024", "G": "1024*1024*1024" } } }
        transformed = multiplex.transform_param_val("size", "16K")
        assert transformed == "16384"

    """Test val range convert None-to-None"""
    def test_convert_range(self):
        multiplex.convert_dict = { "size": { "": { "": "1", "B": "1", "K": "1024", "M": "1024*1024", "G": "1024*1024*1024" } } }
        transformed = multiplex.transform_param_val("size", "1024-2048")
        assert transformed == "1024-2048"

    """Test val range convert None-to-K, KiB"""
    def test_convert_range_K(self):
        multiplex.convert_dict = { "size": { "K": { "": "1/1024", "B": "1/1024", "K": "1", "M": "1024", "G": "1024*1024" } } }
        multiplex.transform_dict = { "size": { "search": "K", "replace": "kiB" } }
        transformed = multiplex.transform_param_val("size", "1024-2048")
        assert transformed == "1kiB-2kiB"
