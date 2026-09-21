#!/bin/python3

import json
import argparse
import copy
import traceback
import os
import logging
import re
import itertools
import math
import threading

from jsonschema import validate
from jsonschema import exceptions
from collections import defaultdict

EC_SUCCESS=0
EC_SCHEMA_FAIL=1
EC_JSON_FAIL=2
EC_REQUIREMENTS_FAIL=3
EC_VALIDATIONS_FAIL=4
EC_REQ_SCHEMA_FAIL=5
EC_EMPTY_SET_FAIL=6
EC_OUTPUT_WRITE_FAIL=7

validation_dict = {}
convert_dict = {}
transform_dict = {}
presets_dict = {}
repeatable_args = {}

_expansion_lock = threading.RLock()


class ExpansionError(ValueError):
    """A structured failure from the importable expansion API."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message

# defined at module scope (not just inside main()) so any function using
# log.* works whether or not main() has run -- e.g. when multiplex.py is
# imported and its functions called directly, as the test suite does.
# main()'s logging.basicConfig() call reconfigures the root logger's
# level/format for CLI use, which this same logger picks up via the
# standard logging hierarchy -- main() never needs to reassign `log`
# itself, since logging.getLogger(__name__) always returns this same
# object.
log = logging.getLogger(__name__)

def is_repeatable(arg):
    """Defaults to False (the original single-occurrence contract) for
    any arg the requirements file never mentions in a 'repeatable'
    validation group, including when there's no requirements file at
    all -- repeatability must be explicitly opted into, never assumed."""
    return repeatable_args.get(arg, False)

def process_options():
    """Process arguments from command line"""
    parser = argparse.ArgumentParser(
        description = 'Translate a JSON with multi-value parameters into a'
                      'JSON with single-value parameters')

    parser.add_argument('--input',
                        dest = 'input',
                        help = 'JSON file with multi-value parameters',
                        default = 'mv-params.json',
                        type = str)

    parser.add_argument('--requirements',
                        dest = 'req',
                        help = 'JSON file with validation and transformation requirements',
                        type = str)

    parser.add_argument('--output',
                        dest = 'output',
                        help = 'JSON output file with single-value parameters',
                        type = str)

    parser.add_argument('--debug',
                        action = 'store_true',
                        help = 'Print debug messages to stderr')

    parser.add_argument('--flat',
                        action = 'store_true',
                        help = 'Treat --input as a flat array of {arg, val'
                               '[, enabled]} params (a single implicit set,'
                               ' no include, no sweep) instead of the'
                               ' general sets/global-options document')

    args = parser.parse_args()
    return args

def dump_json(obj, format = 'readable'):
    """Dump json in readable or parseable format"""
    # Parseable format has no indentation
    indentation = None
    sep = ':'
    if format == 'readable':
        indentation = 4
        sep += ' '

    return json.dumps(obj, indent = indentation, separators = (',', sep),
                      sort_keys = True)

def param_enabled(param_obj):
    """Return True if param is enabled, False otherwise"""
    enabled=True
    if "enabled" in param_obj:
        if param_obj['enabled'].lower() == "no":
            enabled=False
        del param_obj["enabled"]
    return enabled

def param_validated(param, val):
    """Return True if matches validation pattern, False otherwise"""

    # if validation dict is empty, no requirements are in place, then pass
    if len(validation_dict) == 0:
        return True

    valid = False
    if param in validation_dict:
        pattern_array = validation_dict[param]

        # backwards compatibility (validation regex as str, not an array)
        if isinstance(pattern_array, str):
            pattern_array = [pattern_array]

        for pattern in pattern_array:
            if re.match(rf'{pattern}', val) is None:
                log.warning("Validation failed for param='%s', "
                            "val='%s'. Values didn't match the pattern '%s'."
                            % (param, val, pattern))
            else:
                valid = True
    elif bool(validation_dict):
        log.error("Validation for param='%s' not found in the "
                  "requirements file." % param)
    return valid

def _merge_included_param(param, param_set):
    """Deep-copy param and merge it via merge_param_include() unless it's
    disabled -- shared by the 'include' and 'include-preset' handling in
    load_param_sets() below, since both do exactly this."""
    p = copy.deepcopy(param)
    if param_enabled(p):
        merge_param_include(p, param_set)

def load_param_sets(sets_block):
    """Load params from sets block"""
    # mv_array (multi-value) is an array of param set arrays
    mv_array = []

    if len(sets_block) == 0 or "sets" not in sets_block:
        return mv_array

    for set in sets_block['sets']:
        param_set = []

        if not param_enabled(set):
            # ignore this set if enabled=no
            continue

        # handle global params included in each set
        if 'include' in set:
            include_set = set['include']
            # include may be a string or array, normalize it to array
            if isinstance(include_set, str):
                include_set = [ include_set ]
            for inc in include_set:
                # Go find set of params in global options block
                for global_opt in sets_block['global-options']:
                    # Include params if set name matches
                    if inc == global_opt['name']:
                        for global_param in global_opt['params']:
                            _merge_included_param(global_param, param_set)

        # handle named presets params included in each set
        if 'include-preset' in set and set['include-preset'] in presets_dict:
            for param_preset in presets_dict[set['include-preset']]:
                _merge_included_param(param_preset, param_set)

        # handle params in each set. Resolved via _resolve_param_list()
        # (rather than a plain enabled-filtered loop) so a same-arg
        # duplicate within the set's own 'params' -- the single most
        # likely place for a copy-paste mistake -- gets the same
        # diagnostic as the identical shape of conflict in
        # defaults/essentials/include.
        if 'params' in set:
            for param in _resolve_param_list(set['params'], "params"):
                merge_param_own(param, param_set)

        # mv_array is the outter array containing the inner sets
        mv_array.append(param_set)

    return mv_array

def sanitize_set(obj):
    """Update set with roles and remove disabled params or entire set"""

    result = []
    for param in obj:
        if not param_enabled(param):
            continue

        # default to client role if not specified
        if "role" not in param:
            param['role'] = "client"

        result.append(param)

    return result

def transform_param_val(param, val):
    """Param validation, transformation and conversion"""
    # check if param passes validation pattern
    if bool(validation_dict):
        if not param_validated(param, val):
            exit(EC_VALIDATIONS_FAIL)

    if bool(convert_dict):
        if param in convert_dict:
            val_range = val.split('-')
            vals = []
            for v in val_range:
                _unit = re.sub(rf'.*[0-9]([a-zA-Z]+)?$', rf'\1', v)
                _num = re.sub(rf'^(([1-9][0-9]*\.?[0-9]*)|(0?\.[0-9]+)).*', rf'\1', v)
                _convert = next(iter(convert_dict[param]))

                if _unit in convert_dict[param][_convert]:
                    _cexpr = str(convert_dict[param][_convert][_unit])

                    _val = eval(_num + " * " + _cexpr)
                    if float(_val).is_integer():
                        _val = int(_val)
                    vals.append(str(_val) + _convert)
                else:
                    log.warning("Unit %s has not been found in `units`" % _unit)
            if len(vals) > 0:
                val = vals[0]
            if len(vals) > 1:
                val = val + "-" + vals[1]

    if bool(transform_dict):
        if (param in transform_dict and
                "search" in transform_dict[param] and
                "replace" in transform_dict[param]):
            _search = transform_dict[param]["search"]
            _replace = transform_dict[param]["replace"]
            try:
                val = re.sub(rf'{_search}', rf'{_replace}', val)
            except re.error:
                log.exception("Invalid regex for search/replace.")
    return val

def multiplex_set(raw_set):
    """Transform one multi-value set into multiple single-value sets"""
    return list(_multiplex_set_iter(raw_set))


def _prepare_multiplex_set(raw_set):
    """Normalize one set and validate/transform its values once."""
    # step 1: check role, remove disabled params
    obj = sanitize_set(raw_set)
    combinations = []

    # iterate over the original set obj
    for set_idx in range(0, len(obj)):
        _list = []

        # get the number of param vals
        _pvals = len(obj[set_idx]['vals'])
        for copies in range(0, _pvals):
            param = obj[set_idx]['arg']
            val = obj[set_idx]['vals'][copies]

            val = transform_param_val(param, val)

            # step 2: add params vals to a list
            _list.append(val)

        """
        a set with:
            { "arg": "mtu", "vals": ["1518", "9216"] },
            { "arg": "frame-size", "vals": ["64", "9000"] }
        becomes a list of param lists...
            combinations=[[64,9000],[1518,9216]]
        """
        # step 3: append lists to combinations outter list
        combinations.append(_list)

    return obj, combinations


def _multiplex_set_iter(raw_set):
    """Yield one expanded set at a time without materializing the product."""
    obj, combinations = _prepare_multiplex_set(raw_set)

    # step 4: update vals for each combination. Keeping this iterator lazy
    # lets callers enforce a response or cardinality bound before a large
    # Cartesian product is materialized.
    for combination in itertools.product(*combinations):
        expanded = copy.deepcopy(obj)
        for param_idx, param in enumerate(expanded):
            param['vals'] = [combination[param_idx]]
        yield expanded


def _multiplex_set_count(raw_set):
    """Return one set's Cartesian cardinality without building its product."""
    _, combinations = _prepare_multiplex_set(raw_set)
    return math.prod(len(values) for values in combinations)

def update_vals(obj, combinations):
    """Update vals list with the cartesian product"""
    new_obj = []
    """
    a combinations list with:
        combinations=[[64,9000],[1518,9216]]
    becomes a list of tuples (cartesian product):
        cprod =[(64,1518), (64,9216), (9000,1518), (9000,9216)]
    """
    # step 1: build the cartesian product
    cprod = list(itertools.product(*combinations))

    """
    a set with:
        { "arg": "mtu", "vals": ["1518", "9216"] },
        { "arg": "frame-size", "vals": ["64", "9000"] }
    becomes 4 identical copies, unchanged values yet...
        [ <copy 1> ], [ <copy 2> ], [ <copy 3> ], [ <copy 4> ]
    """
    # step 2: create a copy of the entire set for each combination
    for i in range(len(cprod)):
        new_obj.append(copy.deepcopy(obj))

    # step 3: update vals with single value from the cartesian product
    for set_idx in range(0, len(new_obj)):
        for par_idx in range(0, len(new_obj[set_idx])):
            # vals now is an array containing one single val
            new_obj[set_idx][par_idx]['vals'] = [cprod[set_idx][par_idx]]

    return new_obj

def multiplex_sets(obj):
    """Parse multiple sets"""
    multiplexed_sets = []

    for sets_idx in range(0, len(obj)):
        multiplexed_sets.extend(_multiplex_set_iter(obj[sets_idx]))

    return multiplexed_sets


def multiplex_sets_bounded(obj, max_results):
    """Expand sets up to ``max_results`` and report whether more exist.

    The existing ``multiplex_sets`` API remains unbounded for CLI
    compatibility. This variant stops before materializing the first result
    beyond the caller's limit, which is the boundary needed by service APIs.
    """
    if isinstance(max_results, bool) or not isinstance(max_results, int) or max_results < 1:
        raise ExpansionError("invalid_limit", "max_results must be a positive integer")

    total_count = sum(_multiplex_set_count(param_set) for param_set in obj)
    expanded = []
    for param_set in obj:
        for result in _multiplex_set_iter(param_set):
            if len(expanded) >= max_results:
                return expanded, True, total_count
            expanded.append(result)
    return expanded, False, total_count


def _reset_expansion_state():
    """Clear process-global requirement state used by the legacy functions."""
    validation_dict.clear()
    convert_dict.clear()
    transform_dict.clear()
    presets_dict.clear()
    repeatable_args.clear()


def _validate_global_option_includes(input_json):
    """Reject references to global option groups that are not defined."""
    global_options = input_json.get("global-options", [])
    defined_names = {option["name"] for option in global_options}

    for set_index, parameter_set in enumerate(input_json.get("sets", [])):
        includes = parameter_set.get("include", [])
        if isinstance(includes, str):
            includes = [includes]
        for name in includes:
            if name not in defined_names:
                raise ExpansionError(
                    "invalid_input",
                    f"set {set_index} references unknown global-options group: {name}",
                )


def expand_parameters(input_json, requirements_json=None, max_results=None):
    """Expand a multiplex document without invoking the CLI or writing files.

    ``input_json`` and ``requirements_json`` are treated as immutable. The
    returned ``sets`` contain the same single-valued parameter objects emitted
    by the command-line pipeline. When ``max_results`` is provided, ``sets``
    is a bounded prefix and ``truncated`` indicates that more expansions were
    available.

    The legacy implementation stores requirement state in module globals and
    several validation paths use ``SystemExit`` for CLI compatibility. A
    re-entrant lock makes this adapter safe for concurrent library callers,
    while the state reset and structured exception keep calls isolated.
    """
    if not isinstance(input_json, dict):
        raise ExpansionError("invalid_input", "input_json must be an object")
    if requirements_json is not None and not isinstance(requirements_json, dict):
        raise ExpansionError("invalid_requirements", "requirements_json must be an object")
    if max_results is not None and (
        isinstance(max_results, bool) or not isinstance(max_results, int) or max_results < 1
    ):
        raise ExpansionError("invalid_limit", "max_results must be a positive integer")

    with _expansion_lock:
        _reset_expansion_state()
        try:
            if not validate_schema(input_json, "schema.json"):
                raise ExpansionError("invalid_input", "input_json does not match schema.json")
            _validate_global_option_includes(input_json)

            if requirements_json is not None:
                if not validate_schema(requirements_json, "req-schema.json"):
                    raise ExpansionError(
                        "invalid_requirements",
                        "requirements_json does not match req-schema.json",
                    )
                create_validation_dict(copy.deepcopy(requirements_json))
                load_presets(copy.deepcopy(requirements_json))

            combined = load_param_sets(copy.deepcopy(input_json))
            overridden = override_presets(combined)
            if overridden is None:
                raise ExpansionError(
                    "empty_expansion",
                    "input produced an empty parameter set",
                )

            if max_results is None:
                expanded = multiplex_sets(overridden)
                truncated = False
                total_count = len(expanded)
            else:
                expanded, truncated, total_count = multiplex_sets_bounded(
                    overridden, max_results
                )

            return {
                "sets": convert_vals(expanded),
                "count": total_count,
                "returned": len(expanded),
                "truncated": truncated,
            }
        except ExpansionError:
            raise
        except SystemExit as exc:
            raise ExpansionError(
                "expansion_failed",
                f"parameter expansion failed with exit code {exc.code}",
            ) from exc
        finally:
            _reset_expansion_state()

def convert_vals(obj):
    """Convert vals into val for each single-value set"""
    new_obj = copy.deepcopy(obj)

    for param_set in new_obj:
        for param in param_set:
            param['val'] = param['vals'][0]
            del param['vals']

    return new_obj

def load_presets(json_req):
    """Create a dict for presets"""
    if "presets" in json_req:
        presets_dict.update(json_req["presets"])

def _resolve_param_list(entries, label, force_role=None):
    """Return entries filtered to enabled ones only, each deep-copied so
    callers can merge them freely without risk of mutating the original
    list (e.g. presets_dict, or a set's own 'params' straight from the
    input JSON). A disabled entry is excluded before duplicate-conflict
    detection, not after -- it never reaches the target set at all, so
    it must not be allowed to claim an (arg, role, id) identity that a
    later, actually-enabled entry needs, and it must not trigger a false
    conflict warning against an entry that's the only one really active.

    If force_role is given, every entry's role is forced to it (id is
    dropped entirely) before duplicate-conflict detection -- not after --
    so the same identity is used both for detecting a conflict here and
    for the eventual merge_param_own() call against a caller's own
    params. Applying a role override only after resolving would let an
    entry with a leftover/explicit role or id dodge the conflict check
    here and then also fail to match (and therefore fail to override) an
    unrelated same-arg entry at merge time. Used by callers with no
    role/id concept of their own (see apply_flat_params()).

    Also warns (using label to identify which list, e.g. 'defaults' or
    'params') if two entries share the same non-repeatable
    (arg, role, id) -- a likely requirements-file/mv-params authoring
    mistake. The entries are still returned in order, so applying them
    via merge_param_own() naturally makes the last one win, matching
    this file's established last-group-wins convention
    (validation_dict/convert_dict/transform_dict/repeatable_args)."""
    resolved = []
    seen = set()
    for _entry in entries:
        _entry = copy.deepcopy(_entry)
        if force_role is not None:
            _entry['role'] = force_role
            _entry.pop('id', None)
        if not param_enabled(_entry):
            continue
        if not is_repeatable(_entry["arg"]):
            key = _identity_key(_entry)
            if key in seen:
                log.warning(
                    "Multiple %s found for arg='%s' role='%s' id='%s'"
                    " -- the last one takes effect."
                    % ((label,) + key)
                )
            seen.add(key)
        resolved.append(_entry)
    return resolved

def _resolve_preset_group(group_name, force_role=None):
    """_resolve_param_list() over presets_dict[group_name] (defaults or
    essentials) -- see _resolve_param_list() for the full contract. This
    warns once per run (not once per target set, since a preset group is
    a static property of the requirements file itself), unlike a set's
    own 'params' (also resolved via _resolve_param_list(), see
    load_param_sets()) which is necessarily a per-set check."""
    return _resolve_param_list(presets_dict.get(group_name, []), group_name, force_role)

def override_presets(json_obj, force_role=None):
    """Override params w/ presets loaded from the requirements file. See
    _resolve_preset_group() for what force_role does and why it must be
    applied before conflict detection, not after."""

    if len(json_obj) == 0:
        json_obj = [[]]

    # _resolve_preset_group() already returns [] for a group that isn't
    # in presets_dict at all, so no need to pre-check membership here.
    _defaults = _resolve_preset_group("defaults", force_role)
    _essentials = _resolve_preset_group("essentials", force_role)

    for _json in json_obj:
        # apply default params if empty set. Routed through
        # merge_param_own() (instead of a verbatim deepcopy of the whole
        # list) so a 'defaults' preset gets the same duplicate-collapsing
        # protection as essentials/include/own-params -- an accidental
        # same-arg duplicate in the requirements file's own 'defaults'
        # preset would otherwise produce two conflicting values. Each
        # default is deep-copied again here (on top of _resolve_preset_
        # group()'s own copy) so every target set that ends up using
        # defaults gets its own independent objects to mutate.
        if len(_json) == 0:
            idx = json_obj.index(_json)
            new_default_set = []
            for _default in _defaults:
                merge_param_own(copy.deepcopy(_default), new_default_set)
            json_obj[idx] = new_default_set

    for _json in json_obj:
        # apply essential params. _essentials is read-only here (never
        # mutated) so the same essential independently applies to every
        # set that needs it, not just the first one processed.
        # merge_param_own() already implements exactly the semantics
        # essentials need: a repeatable arg is unioned (added only if
        # that exact value isn't already present), a non-repeatable arg
        # replaces whatever's there (or is appended if absent).
        for _ess in _essentials:
            merge_param_own(copy.deepcopy(_ess), _json)

    # If after the overrides, we find an empty set, we cannot continue.
    for _json in json_obj:
        if _json == [] or len(_json) == 0:
            log.error("An empty param set has been found."
                      " Define preset params (essentials and/or defaults)"
                      " in the requirements file for minimum required params.")
            return None

    return json_obj

def apply_flat_params(params, req_json=None):
    """Validate/convert/transform a flat list of {arg, val[, enabled]}
    params (single implicit set; no include, no sweep) against an
    optional requirements file, applying defaults/essentials via
    override_presets() -- the exact same function the general sets-based
    pipeline uses, called on a one-element set list so its per-set loop
    just runs once. This is the path tools use instead of
    load_param_sets()'s include-handling and multiplex_set()'s
    cartesian-product engine, neither of which tools need: a tool always
    has exactly one implicit set, never uses 'include', and (enforced by
    rickshaw's own tool-params.json schema) never has more than one value
    per param. Role has no meaning for a tool, so every param (including
    preset entries, via override_presets()'s force_role) is forced to
    role 'all' rather than multiplex's general 'client' default, to avoid
    spurious identity mismatches against a tool's own params.

    Validates params/req_json against their schemas itself (exiting on
    failure) rather than trusting the caller to have done so -- this is
    meant to be called directly as a library function (as the test suite
    already does), not just via main()'s --flat CLI branch, so it can't
    rely on validation happening somewhere upstream.

    Returns a flat list of {arg, val} dicts, or None if the resulting
    param set is empty (matching override_presets()'s EC_EMPTY_SET_FAIL
    convention)."""
    if not validate_schema(params, "flat-schema.json"):
        exit(EC_SCHEMA_FAIL)

    if req_json is not None:
        if not validate_schema(req_json, "req-schema.json"):
            exit(EC_REQ_SCHEMA_FAIL)
        # Each call represents one tool's own, independent requirements
        # file -- reset everything a *previous* call may have populated
        # so it can't silently leak into this one. Rickshaw only ever
        # invokes multiplex via a fresh subprocess per tool today, so
        # this isn't reachable in production, but the test suite (and
        # any other direct-library caller) calls apply_flat_params()
        # repeatedly in one process.
        presets_dict.clear()
        validation_dict.clear()
        convert_dict.clear()
        transform_dict.clear()
        repeatable_args.clear()
        create_validation_dict(req_json)
        load_presets(req_json)

    # Reshape val -> vals first (own_params is disposable, so the deep
    # copy _resolve_param_list() does internally is enough protection for
    # everything after this point; only the reshape itself must not
    # mutate the caller's own params list). Routed through
    # _resolve_param_list() (rather than an inline enabled-filtered loop)
    # so a same-arg duplicate in a tool's own params -- the actual shape
    # rickshaw's --flat invocation feeds through here -- gets the same
    # diagnostic as the identical conflict in load_param_sets()'s own
    # 'params' handling, defaults, essentials, and include.
    own_params = []
    for param in params:
        p = dict(param)
        p['vals'] = [p.pop('val')]
        own_params.append(p)

    param_set = []
    for param in _resolve_param_list(own_params, "params", force_role='all'):
        merge_param_own(param, param_set)

    overridden = override_presets([param_set], force_role='all')
    if overridden is None:
        return None
    param_set = overridden[0]

    multiplexed = multiplex_sets([param_set])
    if multiplexed is None or len(multiplexed) != 1:
        log.error("Flat params resolved to %s combinations; expected "
                  "exactly one (check for a multi-valued default/essential "
                  "in the requirements file)."
                  % (0 if multiplexed is None else len(multiplexed)))
        exit(EC_VALIDATIONS_FAIL)

    finalized = convert_vals(multiplexed)
    return [{"arg": p["arg"], "val": p["val"]} for p in finalized[0]]

def _identity_key(param):
    """Return the (arg, role, id) tuple used throughout this file to
    decide whether two params represent "the same" logical parameter.
    role/id default to "client"/"1" when absent, matching multiplex's
    general default-role convention (see sanitize_set())."""
    return (
        param["arg"],
        param.get("role", "client"),
        param.get("id", "1"),
    )

def _find_by_identity(param, param_set, match_vals=False):
    """Scan param_set for an entry matching param's (arg, role, id)
    identity, optionally also requiring an identical 'vals'. Shared by
    param_exists()/exact_duplicate_exists() so the two can never disagree
    on what counts as "the same" param."""
    key = _identity_key(param)
    for p in param_set:
        if _identity_key(p) == key:
            if not match_vals or p.get("vals") == param.get("vals"):
                return p
    return None

def param_exists(param, set):
    """Return the matching entry already in the set (by identity), or
    None if param is a new one"""
    return _find_by_identity(param, set)

def exact_duplicate_exists(param, param_set):
    """Check if an entry identical in arg, vals, role, and id already
    exists in param_set. Used for repeatable args, where distinct
    occurrences must all survive but a byte-for-byte duplicate (e.g. the
    same param arriving via both 'include' and a set's own 'params')
    would just run the same command twice for no reason."""
    return _find_by_identity(param, param_set, match_vals=True) is not None

def merge_repeatable_param(param, param_set):
    """If param's arg is repeatable, add it to param_set (unless an exact
    duplicate is already present) and report that the repeatable case was
    handled. Returns False for a non-repeatable arg, leaving it to the
    caller's own replace-or-skip semantics.

    A repeatable arg may have multiple distinct occurrences, but each
    occurrence must be single-valued -- sweeping a repeatable arg's own
    values (multiple vals within one occurrence) has no defined meaning
    yet (would it union all the values together, or multiply them against
    other repeatable occurrences?) and is rejected outright rather than
    silently producing a confusing cross-multiplied result."""
    if not is_repeatable(param['arg']):
        return False
    if len(param.get('vals', [])) > 1:
        log.error("Param '%s' is declared repeatable but has %d values in "
                  "a single occurrence -- sweeping a repeatable arg's "
                  "values is not supported. Declare each value as a "
                  "separate occurrence instead."
                  % (param['arg'], len(param['vals'])))
        exit(EC_VALIDATIONS_FAIL)
    if not exact_duplicate_exists(param, param_set):
        param_set.append(param)
    return True

def merge_param(param, param_set, replace):
    """Add param to param_set. A repeatable arg is always added (unless an
    exact duplicate is already present) and never replaces anything. For a
    non-repeatable arg: if replace is True, an existing same-arg/role/id
    param is replaced (matching a set's own 'params' semantics); if False,
    an existing param wins and this one is skipped (matching
    'include'/'include-preset' semantics), logging a warning since two
    included sources (two global-options groups, or 'include' vs
    'include-preset') sharing an identity is a likely authoring mistake
    -- unlike a set's own 'params' intentionally overriding an included
    value, which is the normal, expected case and not warned about."""
    if merge_repeatable_param(param, param_set):
        return
    existing = param_exists(param, param_set)
    if existing:
        if replace:
            idx = param_set.index(existing)
            param_set[idx] = param
        else:
            log.warning(
                "Multiple included params found for arg='%s' role='%s' "
                "id='%s' -- the first one takes effect."
                % _identity_key(param)
            )
    else:
        param_set.append(param)

def merge_param_include(param, param_set):
    """Add param to param_set, matching 'include'/'include-preset'
    semantics: a same-arg/role/id param already present wins, this one is
    skipped with a warning (unless the arg is repeatable -- see
    merge_param())."""
    merge_param(param, param_set, replace=False)

def merge_param_own(param, param_set):
    """Add param to param_set, matching a set's own 'params' semantics:
    this entry replaces an existing same-arg/role/id param if present
    (unless the arg is repeatable -- see merge_param())."""
    merge_param(param, param_set, replace=True)

def create_validation_dict(req_json):
    """Create validation dict from requirements"""
    validations = req_json["validations"]
    for _vgroup in validations:
        _repeatable = validations[_vgroup].get("repeatable", False)

        for _param in validations[_vgroup]["args"]:
            # last group to declare an arg wins, same conflict-resolution
            # rule validation_dict/convert_dict/transform_dict already use
            # below -- an arg isn't expected to appear in more than one
            # group, but if it does, this keeps repeatable_args consistent
            # with how the rest of this function resolves the same case
            repeatable_args[_param] = _repeatable

            _vals = validations[_vgroup]["vals"]
            _pattern = { _param: _vals }
            validation_dict.update(_pattern)

            if "convert" in validations[_vgroup]:
                _convert = validations[_vgroup]["convert"]
                if "units" in req_json and len(req_json["units"]) > 0:
                    if _vgroup in req_json["units"]:
                        if _convert in req_json["units"][_vgroup]:
                            _cexpr = req_json["units"][_vgroup][_convert]
                            _conversion = { _convert: _cexpr }
                            convert_dict.update({ _param: _conversion })
                        else:
                            log.warning("Conversion '%s' has not been found "
                                        " and will be skipped.", _convert)
                    else:
                        log.warning("No conversion has been found "
                                     "for the param '%s'.", _param)
                else:
                    log.warning("The 'units' section has not been found. "
                                "Ignoring all conversions.")

            if "transform" in validations[_vgroup]:
                _transform = validations[_vgroup]["transform"]
                _replace = { _param: _transform }
                transform_dict.update(_replace)

def load_json_file(json_file):
    """Load JSON file and return a json object"""
    try:
        input_fp = open(json_file, 'r')
        input_json = json.load(input_fp)
        input_fp.close()
    except:
        log.exception("Could not load JSON file %s" % (json_file))
        return None
    return input_json

def validate_schema(input_json, schema_file):
    """Validate json with schema file"""
    json_schema_file = "%s/JSON/%s" % (os.path.dirname(os.path.abspath(__file__)), schema_file)
    try:
        schema_fp = open(json_schema_file, 'r')
        schema_contents = json.load(schema_fp)
        schema_fp.close()
        validate(instance = input_json, schema = schema_contents)
    except:
        log.exception("JSON validation failed using schema %s", json_schema_file)
        return False
    return True

def dump_output(final_json):
    """Dump output multiplexed json to stdout or file"""
    if args.output is None:
        # dump to stdout
        print(dump_json(final_json))
    else:
        # dump to --output file
        try:
            output_file=open(args.output,mode="w",encoding="utf-8")
            output_file.write(dump_json(final_json))
            output_file.close()
        except:
            log.exception("Failed to write to file %s" % (args.output))
            exit(EC_OUTPUT_WRITE_FAIL)

def main():
    """Main function of multiplex"""

    global args

    logformat = '%(asctime)s %(levelname)s %(name)s:  %(message)s'
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format=logformat)
    else:
        logging.basicConfig(level=logging.INFO, format=logformat)

    if args.flat:
        input_json = load_json_file(args.input)
        if input_json is None:
            return EC_JSON_FAIL

        json_req = None
        if args.req is not None:
            json_req = load_json_file(args.req)
            if json_req is None:
                return EC_REQUIREMENTS_FAIL

        # Schema validation for both input_json and json_req happens
        # inside apply_flat_params() itself (it exits on failure), since
        # it's meant to be safely callable as a library function too, not
        # just from this CLI branch.
        result = apply_flat_params(input_json, json_req)
        if result is None:
            return EC_EMPTY_SET_FAIL

        dump_output(result)
        return EC_SUCCESS

    input_json = load_json_file(args.input)

    if input_json is None:
        return EC_JSON_FAIL
    if not validate_schema(input_json, "schema.json"):
        return EC_SCHEMA_FAIL

    if args.req is not None:
        json_req = load_json_file(args.req)
        if json_req is None:
            return EC_REQUIREMENTS_FAIL
        if not validate_schema(json_req, "req-schema.json"):
            return EC_REQ_SCHEMA_FAIL
        create_validation_dict(json_req)
        load_presets(json_req)

    combined_json = load_param_sets(input_json)

    overriden_json = override_presets(combined_json)
    if overriden_json == None:
        return EC_EMPTY_SET_FAIL

    multiplexed_json = multiplex_sets(overriden_json)
    finalized_json = convert_vals(multiplexed_json)
    dump_output(finalized_json)

    return EC_SUCCESS


if __name__ == "__main__":
    args = process_options()
    exit(main())
