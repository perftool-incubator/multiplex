#!/bin/python3

import json
import argparse
import copy
import traceback
import os
import logging
import re
import itertools

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

validation_dict = {}
convert_dict = {}
transform_dict = {}
presets_dict = {}

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

def load_param_sets(sets_block):
    """Load params from sets block"""
    # mv_array (multi-value) is an array of param set arrays
    mv_array = []

    if len(sets_block) == 0 or "sets" not in sets_block:
        return mv_array

    for set in sets_block['sets']:
        param_set = []

        # handle global params included in each set
        if 'include' in set:
            # Go find set of params in global options block
            for global_opt in sets_block['global-options']:
                # Include params if set name matches
                if set['include'] == global_opt['name']:
                    for global_param in global_opt['params']:
                        # only include if param is not defined in this set
                        if (param_enabled(global_param) and not
                            param_exists(global_param, param_set)):
                            param_set.append(copy.deepcopy(global_param))

        # handle named presets params included in each set
        if 'include-preset' in set:
            # Go find group of params in requirements presets
            for preset_grp in presets_dict:
                # Include params if named-preset group is found
                if set['include-preset'] in presets_dict:
                    for param_preset in presets_dict[set['include-preset']]:
                        # only include if param is not defined in this set
                        if (param_enabled(param_preset) and not
                            param_exists(param_preset, param_set)):
                            param_set.append(copy.deepcopy(param_preset))

        # handle params in each set
        if 'params' in set:
            for param in set['params']:
                if param_enabled(param):
                    replace_param = param_exists(param, param_set)
                    if replace_param:
                        idx = param_set.index(replace_param)
                        param_set[idx] = param
                    else:
                        param_set.append(param)

        # mv_array is the outter array containing the inner sets
        mv_array.append(param_set)

    return mv_array

def sanitize_set(obj):
    """Update set with roles and remove disabled params"""
    for set_idx in range(0, len(obj)):

        # remove param from the set obj if not enabled
        if not param_enabled(obj[set_idx]):
            del obj[set_idx]
            continue

        # default to client role if not specified
        if "role" not in obj[set_idx]:
            obj[set_idx]['role'] = "client"

    return obj

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

    # step 4: update vals for all combinations
    _obj = update_vals(obj, combinations)
    return _obj

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
        new_set = multiplex_set(obj[sets_idx])
        if new_set is None:
            return None
        if len(new_set):
            multiplexed_sets += new_set

    return multiplexed_sets

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

def override_presets(json_obj):
    """Override params w/ presets loaded from the requirements file"""

    if len(json_obj) == 0:
        json_obj = [[]]

    for _json in json_obj:
        # apply default params if empty set
        if "defaults" in presets_dict:
            if len(_json) == 0:
                idx = json_obj.index(_json)
                json_obj[idx] = copy.deepcopy(presets_dict["defaults"])

    for _json in json_obj:
        # append essential params, override duplicates
        if "essentials" in presets_dict:
            for _param in _json:
                _ess = next((item for item in presets_dict["essentials"]
                             if item["arg"] == _param["arg"]), False)
                if _ess:
                    # override param with essential
                    idx = _json.index(_param)
                    _json[idx] = _ess

                    # delete overriden param from essentials
                    idx = presets_dict["essentials"].index(_ess)
                    del presets_dict["essentials"][idx]

            if len(_json) > 0:
                # append essentials (new/undefined ones)
                for _ess in presets_dict["essentials"]:
                    _json.append(_ess)
            else:
                idx = json_obj.index(_json)
                json_obj[idx] = copy.deepcopy(presets_dict["essentials"])

    # If after the overrides, we find an empty set, we cannot continue.
    for _json in json_obj:
        if _json == [] or len(_json) == 0:
            log.error("An empty param set has been found."
                      " Define preset params (essentials and/or defaults)"
                      " in the requirements file for minimum required params.")
            return None

    return json_obj

def param_exists(param, set):
    """Check if param is already defined in the set or it is a new one"""

    param_role = "client"
    param_id = "1"

    if "role" in param:
        param_role = param["role"]
    if "id" in param:
        param_id = param["id"]

    for p in set:
        if param["arg"] == p["arg"]:
            if "role" in p:
                p_role = p["role"]
            else:
                p_role = "client"
            if "id" in p:
                p_id = p["id"]
            else:
                p_id = "1"
            if param_role == p_role and param_id == p_id:
                return p

    return False

def create_validation_dict(req_json):
    """Create validation dict from requirements"""
    validations = req_json["validations"]
    for _vgroup in validations:
        for _param in validations[_vgroup]["args"]:
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
        log.exception("JSON validation failed for %s using schema %s"
                      % (input_json, json_schema_file))
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
    global log

    logformat = '%(asctime)s %(levelname)s %(name)s:  %(message)s'
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format=logformat)
    else:
        logging.basicConfig(level=logging.INFO, format=logformat)
    log = logging.getLogger(__name__)

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
