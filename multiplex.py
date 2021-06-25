#!/bin/python3

import json
import argparse
import copy
import traceback
import os
import logging

from jsonschema import validate
from jsonschema import exceptions

EC_SUCCESS=0
EC_SCHEMA_FAIL=1
EC_JSON_FAIL=2
EC_REQUIREMENTS_FAIL=3


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

    parser.add_argument('--debug',
                        action = 'store_true',
                        help = 'Print debug messages to stderr')

    args = parser.parse_args()
    return(args)


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
    return(enabled)


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
                            param_set.append(global_param)

        # handle params in each set
        if 'params' in set:
            for param in set['params']:
                if param_enabled(param):
                    param_set.append(param)

        # mv_array is the outter array containing the inner sets
        mv_array.append(param_set)

    return(mv_array)


def multiplex_set(obj):
    """Parse vals from one set"""
    new_obj = []

    for set_idx in range(0, len(obj)):

        # ignores/skips param if not enabled
        if not param_enabled(obj[set_idx]):
            continue

        # default to client role if not specified
        if "role" not in obj[set_idx]:
            obj[set_idx]['role'] = "client"

        if len(obj[set_idx]['vals']) > 1:
            for copies in range(0, len(obj[set_idx]['vals'])):
                new_obj.append(copy.deepcopy(obj))
                new_idx = len(new_obj) - 1
                for copy_idx in range(len(new_obj[new_idx][set_idx]['vals']) - 1, -1, -1):
                    if copy_idx != copies:
                        del new_obj[new_idx][set_idx]['vals'][copy_idx]

            break

    return(new_obj)


def multiplex_sets(obj):
    """Parse multiple sets"""
    new_obj = copy.deepcopy(obj)

    restart = True
    while restart:
        restart = False

        for sets_idx in range(0, len(new_obj)):
            new_sets = multiplex_set(new_obj[sets_idx])
            if len(new_sets):
                restart = True
                del new_obj[sets_idx]

                for new_set_idx in range(0, len(new_sets)):
                    new_obj.insert(sets_idx + new_set_idx, new_sets[new_set_idx])

                break

    return(new_obj)


def convert_vals(obj):
    """Convert vals into val for each single-value set"""
    new_obj = copy.deepcopy(obj)

    for param_set in new_obj:
        for param in param_set:
            param['val'] = param['vals'][0]
            del param['vals']

    return(new_obj)


def load_requirements(req_arg):
    """Load requirements json file from --requirements arg"""
    #TODO: requirements file is loaded but still noop
    try:
        req_fp = open(req_arg, 'r')
        req_json = json.load(req_fp)
        req_fp.close()
    except:
        log.exception("Could not load requirements file %s" % (req_arg))
        return(None)
    return(req_json)

def load_input_file(mv_file):
    try:
        input_fp = open(mv_file, 'r')
        input_json = json.load(input_fp)
        input_fp.close()
    except:
        log.exception("Could not load input file %s" % (mv_file))
        return(None)
    return(input_json)

def validate_schema(input_json):
    json_schema_file = "%s/%s" % (os.path.dirname(os.path.abspath(__file__)),
                                  "schema.json")
    try:
        schema_fp = open(json_schema_file, 'r')
        schema_contents = json.load(schema_fp)
        schema_fp.close()
        validate(instance = input_json, schema = schema_contents)
    except IOError:
        log.exception("Could not open schema file %s" % (json_schema_file))
        return(False)
    except ValueError:
        log.exception("Could not load a valid JSON schema from %s"
                      % (json_schema_file))
        return(False)
    except ValueError:
        log.exception("JSON validation failed for %s using schema %s"
                      % (input_json, json_schema_file))
        return(False)
    return(True)


def main():

    global log
    global args

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
        if load_requirements(args.req) is None:
            return(EC_REQUIREMENTS_FAIL)

    combined_json = load_param_sets(input_json)
    multiplexed_json = multiplex_sets(combined_json)
    finalized_json = convert_vals(multiplexed_json)

    print(dump_json(finalized_json))

    return(EC_SUCCESS)


if __name__ == "__main__":
    args = process_options()
    exit(main())
