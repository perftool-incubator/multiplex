#!/usr/bin/env python3

import pytest
import multiplex

class TestFlat:

    """Test that own params pass through unchanged when no requirements
    file is given"""
    def test_own_params_pass_through_no_requirements(self, reset_presets_dict):
        multiplex.presets_dict = {}
        result = multiplex.apply_flat_params(
            [ { "arg": "interval", "val": "5" } ]
        )
        assert result == [ { "arg": "interval", "val": "5" } ]

    """Test that a disabled own param is excluded from the result"""
    def test_disabled_own_param_excluded(self, reset_presets_dict):
        multiplex.presets_dict = { "essentials": [] }
        result = multiplex.apply_flat_params(
            [ { "arg": "interval", "val": "5", "enabled": "no" } ]
        )
        assert result is None

    """Test that defaults apply only when no own params are given -- an
    own param anywhere makes the whole set non-empty, matching
    override_presets()'s existing all-or-nothing defaults contract for
    benchmarks (see docs/implementing-a-new-tool.md's warning that a
    tool's defaults preset must reproduce its script's own bash-level
    defaults in full, not per-arg)"""
    def test_defaults_apply_only_when_params_empty(self, reset_presets_dict):
        multiplex.presets_dict = {
            "defaults": [
                { "arg": "subtools", "vals": [ "turbostat" ] },
                { "arg": "interval", "vals": [ "10" ] },
            ]
        }

        empty_result = multiplex.apply_flat_params([])
        assert sorted(empty_result, key=lambda p: p["arg"]) == [
            { "arg": "interval", "val": "10" },
            { "arg": "subtools", "val": "turbostat" },
        ]

        own_param_result = multiplex.apply_flat_params(
            [ { "arg": "interval", "val": "5" } ]
        )
        assert own_param_result == [ { "arg": "interval", "val": "5" } ]

    """Test that essentials always apply, regardless of whether own params
    were given"""
    def test_essentials_always_apply(self, reset_presets_dict):
        multiplex.presets_dict = {
            "essentials": [ { "arg": "output-format", "vals": [ "json" ] } ]
        }
        result = multiplex.apply_flat_params(
            [ { "arg": "interval", "val": "5" } ]
        )
        assert sorted(result, key=lambda p: p["arg"]) == [
            { "arg": "interval", "val": "5" },
            { "arg": "output-format", "val": "json" },
        ]

    """Test that multiple occurrences of a repeatable arg all survive"""
    def test_repeatable_occurrences_survive(self, reset_presets_dict):
        multiplex.presets_dict = {}
        multiplex.repeatable_args = { "sysfs-trace-setup": True }
        result = multiplex.apply_flat_params([
            { "arg": "sysfs-trace-setup", "val": "cmd-a" },
            { "arg": "sysfs-trace-setup", "val": "cmd-b" },
        ])
        assert result == [
            { "arg": "sysfs-trace-setup", "val": "cmd-a" },
            { "arg": "sysfs-trace-setup", "val": "cmd-b" },
        ]

    """Test the real tool-kernel shape end-to-end: an own param validated
    against a real requirements file. Defaults are all-or-nothing per
    set (see test_defaults_apply_only_when_params_empty), so supplying
    'interval' here means 'subtools' is NOT backfilled -- this test
    documents that outcome for the real tool-kernel defaults/validations
    shape specifically, it doesn't test per-arg backfill (which doesn't
    exist)"""
    def test_tool_kernel_real_world_shape(self, reset_presets_dict):
        req_json = {
            "presets": {
                "defaults": [
                    { "arg": "subtools", "vals": [ "turbostat" ] },
                    { "arg": "interval", "vals": [ "10" ] },
                ]
            },
            "validations": {
                "subtool_list": {
                    "args": [ "subtools" ],
                    "vals": "^(turbostat|perf)(,(turbostat|perf))*$",
                },
                "positive_integer": {
                    "args": [ "interval" ],
                    "vals": "^[1-9][0-9]*$",
                },
            },
        }
        result = multiplex.apply_flat_params(
            [ { "arg": "interval", "val": "5" } ], req_json
        )
        assert result == [ { "arg": "interval", "val": "5" } ]

    """Test that a multi-valued, non-repeatable default triggers the
    'more than one combination' exit path -- flat mode has no sweep
    concept, so a default sweeping multiple values is a misconfiguration,
    not a silently-truncated result"""
    def test_multi_valued_default_exits(self, reset_presets_dict):
        multiplex.presets_dict = {
            "defaults": [ { "arg": "subtools", "vals": [ "turbostat", "perf" ] } ]
        }
        with pytest.raises(SystemExit):
            multiplex.apply_flat_params([])

    """Test that an entirely empty result (no params, no defaults, no
    essentials) returns None"""
    def test_empty_result_returns_none(self, reset_presets_dict):
        multiplex.presets_dict = {}
        result = multiplex.apply_flat_params([])
        assert result is None

    """Test that apply_flat_params() exits cleanly (rather than crashing
    with TypeError on len(None)) if multiplex_sets() were ever to return
    None -- currently unreachable via the public API, but defended
    against explicitly since multiplex_sets() documents that contract"""
    def test_multiplex_sets_returning_none_exits_cleanly(self, reset_presets_dict, monkeypatch):
        multiplex.presets_dict = {}
        monkeypatch.setattr(multiplex, "multiplex_sets", lambda obj: None)
        with pytest.raises(SystemExit):
            multiplex.apply_flat_params([ { "arg": "interval", "val": "5" } ])

    """Test that a same-arg duplicate in the tool's own params list logs
    a warning -- rickshaw's --flat invocation feeds a tool's params
    through exactly this path, so this is the shape a real copy-paste
    mistake in tool-params.json would take"""
    def test_own_params_conflict_warns(self, reset_presets_dict, caplog):
        multiplex.presets_dict = {}
        result = multiplex.apply_flat_params([
            { "arg": "interval", "val": "5" },
            { "arg": "interval", "val": "10" },
        ])
        assert result == [ { "arg": "interval", "val": "10" } ]
        assert "Multiple params found" in caplog.text

    """Test that a requirements file's presets/validations/repeatable
    state from one call doesn't leak into a later, unrelated call in the
    same process -- a real bug found via review: presets_dict.update()
    only overwrites keys the new file actually defines, so a stale
    'essentials' from a prior call previously survived untouched"""
    def test_state_does_not_leak_between_calls(self, reset_presets_dict):
        multiplex.presets_dict = {}
        req_with_essential = {
            "presets": { "essentials": [ { "arg": "output-format", "vals": [ "json" ] } ] },
            "validations": {},
        }
        multiplex.apply_flat_params(
            [ { "arg": "interval", "val": "5" } ], req_with_essential
        )

        req_without_presets = { "validations": {} }
        result = multiplex.apply_flat_params(
            [ { "arg": "interval", "val": "5" } ], req_without_presets
        )
        assert result == [ { "arg": "interval", "val": "5" } ]

    """Test that repeatable_args from one call's requirements file
    doesn't leak into a later, unrelated call -- the same state-leak bug
    as above, for repeatable_args specifically"""
    def test_repeatable_args_does_not_leak_between_calls(self, reset_presets_dict):
        multiplex.presets_dict = {}
        req_repeatable = {
            "validations": { "g": { "args": [ "output-format" ], "vals": ".+", "repeatable": True } }
        }
        multiplex.apply_flat_params(
            [ { "arg": "output-format", "val": "a" } ], req_repeatable
        )
        assert multiplex.is_repeatable("output-format") is True

        req_unrelated = { "validations": { "g2": { "args": [ "interval" ], "vals": ".+" } } }
        multiplex.apply_flat_params(
            [ { "arg": "interval", "val": "5" } ], req_unrelated
        )
        assert multiplex.is_repeatable("output-format") is False

    """Test that a non-boolean 'repeatable' value (a plausible mistake by
    analogy with 'enabled''s yes/no string convention) is rejected at the
    schema-validation boundary rather than silently misbehaving (a
    Python-truthy non-bool would otherwise make is_repeatable() return
    something other than True/False)"""
    def test_non_boolean_repeatable_rejected(self, reset_presets_dict):
        multiplex.presets_dict = {}
        req_bad = {
            "validations": { "g": { "args": [ "foo" ], "vals": ".+", "repeatable": "no" } }
        }
        with pytest.raises(SystemExit):
            multiplex.apply_flat_params([ { "arg": "foo", "val": "x" } ], req_bad)

    """Test that a malformed param (missing 'val') is rejected at the
    schema-validation boundary with a clean exit rather than an uncaught
    KeyError -- apply_flat_params() is meant to be safely callable
    directly, not just via main()'s --flat CLI branch"""
    def test_malformed_param_rejected_cleanly(self, reset_presets_dict):
        multiplex.presets_dict = {}
        with pytest.raises(SystemExit):
            multiplex.apply_flat_params([ { "arg": "interval" } ])
