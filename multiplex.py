#!/usr/bin/python3

import json
import argparse
import copy


class t_global(object):
    args = None


def process_options():
    parser = argparse.ArgumentParser(description = 'Translate a JSON with multi-value parameters into a JSON with single-value parameters')

    parser.add_argument('--input',
                        dest = 'input',
                        help = 'JSON file with multi-value parameters',
                        default = 'bench-params.json',
                        type = str)

    t_global.args = parser.parse_args()
    return(0)


def dump_json(obj, format = 'readable'):
    if format == 'readable':
        return json.dumps(obj, indent = 4, separators = (',', ': '), sort_keys = True)
    elif format == 'parsable':
        return json.dump(obj, separators = (',', ':'), sort_keys = True)

    return(None)


def handle_common(obj):
    new_obj = copy.deepcopy(obj['sets'])

    for sets_idx in range(0, len(new_obj)):
        restart = True
        while restart:
            restart = False
            found_match = False
            for mv_param_idx in range(0, len(new_obj[sets_idx])):
                if 'common' in new_obj[sets_idx][mv_param_idx]:
                    for common_param_set in obj['common']:
                        if new_obj[sets_idx][mv_param_idx]['common'] == common_param_set['name']:
                            found_match = True
                            del new_obj[sets_idx][mv_param_idx]
                            for insert_offset in range(0, len(common_param_set['params'])):
                                new_obj[sets_idx].insert(mv_param_idx + insert_offset, common_param_set['params'][insert_offset])
                            break
                    if found_match:
                        break
            if found_match:
                restart = True

    return(new_obj)


def multiplex_set(obj):
    new_obj = []

    for set_idx in range(0, len(obj)):
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
    new_obj = copy.deepcopy(obj)

    for param_set in new_obj:
        for param in param_set:
            param['val'] = param['vals'][0]
            del param['vals']

    return(new_obj)


def main():
    input_json = None

    try:
        input_fp = open(t_global.args.input, 'r')
        input_json = json.load(input_fp)
        input_fp.close()
    except:
        print("ERROR: Could not load input file %s" % (t_global.args.input))
        return(1)

    # validate the json here

    combined_json = handle_common(input_json)
    multiplexed_json = multiplex_sets(combined_json)
    finalized_json = convert_vals(multiplexed_json)

    print(dump_json(finalized_json))

    return(0)


if __name__ == "__main__":
    process_options()

    exit(main())
