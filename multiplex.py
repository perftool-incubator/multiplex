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

validation_dict = {}
convert_dict = {}
transform_dict = {}

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
    if param in validation_dict:
        pattern = validation_dict[param]
        if re.match(pattern, val) is None:
            log.error("Validation failed for param='%s', "
                      "val='%s'. Values must match the pattern '%s'."
                      % (param, val, pattern))
            return False
    return True

def load_param_sets(sets_block):
    """Load params from sets block"""
    # mv_array (multi-value) is an array of param set arrays
    mv_array = []

    for set in sets_block['sets']:
        param_set = []

        # handle global params included in each set
        if 'include' in set:
            # Go find set of params in global options block
            for global_opt in sets_block['global-options']:
                # Include params if set name matches
                if set['include'] == global_opt['name']:
                    for global_param in global_opt['params']:
                        if param_enabled(global_param):
                            param_set.append(copy.deepcopy(global_param))

        # handle params in each set
        if 'params' in set:
            for param in set['params']:
                if param_enabled(param):
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
            _unit = re.sub(r"[^A-Za-z]+", "", val).upper()
            _num = str(float(re.sub(r"[^0123456789\.]", "", val)))
            _convert = next(iter(convert_dict[param]))
            _cexpr = str(convert_dict[param][_convert][_unit])

            _val = eval(_num + " * " + _cexpr)
            if float(_val).is_integer():
                _val = int(_val)
            val = str(_val) + _convert

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

def load_requirements(req_arg):
    """Load requirements json file from --requirements arg"""

    #TODO: requirements file is loaded but still noop
    try:
        req_fp = open(req_arg, 'r')
        req_json = json.load(req_fp)
        req_fp.close()
    except:
        log.exception("Could not load requirements file %s" % (req_arg))
        return None

    return req_json

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

def load_input_file(mv_file):
    """Load input file with multi-value params and return a json object"""
    try:
        input_fp = open(mv_file, 'r')
        input_json = json.load(input_fp)
        input_fp.close()
    except:
        log.exception("Could not load input file %s" % (mv_file))
        return(None)
    return input_json

def validate_schema(input_json):
    """Validate json with schema file"""
    json_schema_file = "%s/%s" % (os.path.dirname(os.path.abspath(__file__)), "schema.json")
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

    input_json = load_input_file(args.input)

    if input_json is None:
        return(EC_JSON_FAIL)
    if not validate_schema(input_json):
        return(EC_SCHEMA_FAIL)

    if args.req is not None:
        json_req = load_requirements(args.req)
        if json_req is None:
            return(EC_REQUIREMENTS_FAIL)
        else:
            create_validation_dict(json_req)

    combined_json = load_param_sets(input_json)
    multiplexed_json = multiplex_sets(combined_json)

    finalized_json = convert_vals(multiplexed_json)
    dump_output(finalized_json)

    return EC_SUCCESS


if __name__ == "__main__":
    args = process_options()
    exit(main())
