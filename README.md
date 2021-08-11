# multiplex
[![CI Actions Status](https://github.com/perftool-incubator/multiplex/workflows/unittest/badge.svg)](https://github.com/perftool-incubator/multiplex/actions)

Translates a JSON with multi-value parameters into a JSON with single-value parameters.

## Introduction
When running a benchmark, it is often desirable to run it multiple ways, changing how the options are used, so you can get a full characterization of whatever you are testing.  For example, one might use several message sizes for a network test, or use different IO-engines for a storage test.  However, when executing a benchmark, most of them expect to have exactly one value for each option, like a message-size of just "16k" or an IO-engine of just "libaio".  Multiplex will translate your multi-value options into a list of multiple command-line statements that your benchmark understands.

## Usage
```
./multiplex.py [--requirements JSON/requirements.json] --input JSON/mv-params-input.json [--output /path/to/bench-params.json]
```

## Input multi-value JSON
Multiplex requires a JSON file with the following format:
```
{
    "global-options": [
        {
            "name": "common-params",
            "params": [
                { "arg": "bs", "vals": [ "4k", "8k" ], "role": "client" },
                { "arg": "rw", "vals": [ "read", "write" ], "enabled": "no" }
            ]
        }
    ],
    "sets": [
        {
            "include": "common-params",
            "params": [
                { "arg": "ioengine", "vals": [ "sync" ] }
            ]
        }
    ]
}
```

### global-options
The `global-options` section is required. It contains blocks of general configuration
data that can be replicated and included in the `sets` section.
In this section, you may have an array of multi-value parameters that are common to
the test run such as "common-params". Multi-value params are specified with the `args`
and `vals` keywords. The `role` key is optional and defaults to 'client' if omitted.
Valid roles are: "client", "server" and "all".

These blocks must have "name" and "params" key values.

### sets
A data set of multi-value parameters is defined in each block inside the `sets` section.
The `sets` section is required and must have one or more set(s). Multi-value params are
specified with the `args` and `vals` keywords, identical to the "common-params" block
from the `global-options`. Likewise, the `role` key is optional and defaults to 'client'
if omitted. Valid roles are "client", "server" and "all".

It is also possible to enable/disable params by marking them as `enabled`.
The schema accepts either `yes` and `no` values for the `enabled` keyword, as shown
below:
```
    { "arg": "bs", "vals": [ "4k", "8k" ], "role": "client", "enabled": "no" },
    { "arg": "rw", "vals": [ "read", "write" ], "enabled": "yes" }
```
Marking params as enabled ("enabled": "yes") or disabled ("enabled": "no") is optional.
Multiplex assumes that the param is enabled by default when the `enabled` keyword is not
present. All the `enabled` markers are stripped from the input json file.

For multiple instances of the same role, params can be distinguished by  using the `id`
key as follows:
```
    { "arg": "ifname", "vals": [ "eth1", "eth2" ], "role": "server", "id": "1" },
    { "arg": "ifname", "vals": [ "net1", "net2" ], "role": "server", "id": "2" }
```

## Requirements file
The requirements file defines all the validation and transformation parameters for a
specific benchmark. The file contains the following blocks: `defaults` and `essentials`,
as part of the `presets` section; `validations` and `units` are the other sections.
The example below is a simplified version of fio benchmark requirements file:
```
{
    "presets": {
        "essentials": [
            { "arg": "write_iops_log", "vals": ["fio"] },
            { "arg": "write_lat_log", "vals": ["fio"] }
        ],
        "defaults": [
            { "arg": "rw", "vals": ["read", "randread"] },
            { "arg": "bs", "vals": ["16k"] }
        ],
        "sequential-read": [
            { "arg": "rw", "vals": [ "read" ] },
            { "arg": "bs", "vals": [ "4k" ] }
        ]
    },
    "validations": {
        "size_BKMG": {
            "description": "bytes in B/K/M/G, converted to K, transformed in KB",
            "args": [ "frame-size" ],
            "vals": "[0-9]+[BKMG]?",
            "convert": "K",
            "transform": {
                "search": "[^0123456789\\.]",
                "replace": "KB"
            }
        },
        "log_types" : {
            "description" : "all possible log types",
            "args" : [ "write_bw_log", "write_hist_log", "write_iolog", "write_iops_log", "write_lat_log" ],
            "vals" : "^fio$"
        },
        "rw_types" : {
            "description" : "all possible testtypes",
            "args" : [ "rw" ],
            "vals" : "^(|rand)(read|write|trim)$|^readwrite$|^randrw$|^trimwrite$"
        }
    },
    "units": {
       "size_BKMG": {
            "": { "": "1", "B": "1", "K": "1024", "M": "1024*1024", "G": "1024*1024*1024" },
            "B": { "": "1", "B": "1", "K": "1024", "M": "1024*1024", "G": "1024*1024*1024" },
            "K": { "": "1/1024", "B": "1/1024", "K": "1", "M": "1024", "G": "1024*1024" },
            "M": { "": "1/1024/1024", "B": "1/1024/1024", "K": "1/1024", "M": "1", "G": "1024" },
            "G": { "": "1/1024/1024/1024", "B": "1/1024/1024/1024", "K": "1/1024/1024", "M": "1/1024", "G": "1" }
        }
    }
}
```

The order of precedence for overriding params is the following:
    1. `essentials`: always use (override params defined elsewhere).
    2. param sets defined in the input file: apply params overriding defaults and
       `presets`.
    3. `presets`: override all default params with the params in the `presets`
       array.
    4. `defaults`: only use if not defined anywhere else.

### presets

The presets array is composed by 3 types of elements: `defaults`,
`essentials` and all sets of params that should override the params from
the `defaults` section. Params defined in the `presets` section allow the
benchmark to create a list of pre-defined parameter sets for the user to
easily run a variety of tests.

#### defaults
The `defaults` parameters are used if no parameters are supplied in the input
file by the user. Multiplex assumes the default value if the param is not
present in the multi-value json file neither in the `presets` section of the
requirements file.

#### essentials
The `essentials` parameters are the minimum parameters that the test harness
need to function properly. Theses parameters are always appended to the list of
parameters to use to guarantee basic functionality of the harness.


### validations
Defines all the acceptable param values by validating the parameters with the
`value` regex. The values are transformed by applying the `transform` regex,
if present. The `transform` key (optional) contains the `search` and `replace`
regular expressions to substitute the `vals` key from the multi-value params
file.

Note: The regex pair `search`/`replace` must be in raw string format to
match and process the substitutions w/ backslashes (escapes) properly. Also,
since the JSON has its own escaping, backslashes must be doubled. For instance,
"[^0123456789\.]" becomes "[^0123456789\\.]" to match all numeric values w/
decimal point.

Param transformation happens after the param conversion. If the `convert` key
is "K", and tranformation replace is "KB", the value "1024" is first converted
to K, "1K" and then transformed to KB, "1KB". The benchmark will receive the
param value as "1KB".

### units
Defines all the conversion units to each of the param types. Multiplex converts
the contents of `vals` into the target `convert` key by executing the
expressions from the `units` section.

The param group defined in the `validations` should match the group in the
`units` section. For a given `size_BKMG`, which might contain multiple args as
"frame-size", "mtu", etc., multiplex finds an equivalent `size_BKMG` in the units
section to do the conversions.

## Output single-value JSON
Each data set from the `sets` section, combined with the multi-value paramters included
from the "global-options", are processed and expanded to a new structure of single-value
parameters to STDOUT. A sample is available in `JSON/bench-params-output.json`:
```
[
    [
        {
            "arg": "bs",
            "role": "client",
            "val": "4k"
        },
        {
            "arg": "rw",
            "role": "client",
            "val": "read"
        },
        {
            "arg": "ioengine",
            "role": "client",
            "val": "sync"
        }
    ],
    [
        {
            "arg": "bs",
            "role": "client",
            "val": "4k"
        },
        {
            "arg": "rw",
            "role": "client",
            "val": "write"
        },
        {
            "arg": "ioengine",
            "role": "client",
            "val": "sync"
        }
    ],
    [
        {
            "arg": "bs",
            "role": "client",
            "val": "8k"
        },
        {
            "arg": "rw",
            "role": "client",
            "val": "read"
        },
        {
            "arg": "ioengine",
            "role": "client",
            "val": "sync"
        }
    ],
    [
        {
            "arg": "bs",
            "role": "client",
            "val": "8k"
        },
        {
            "arg": "rw",
            "role": "client",
            "val": "write"
        },
        {
            "arg": "ioengine",
            "role": "client",
            "val": "sync"
        }
    ]
]
```

This JSON can then optionally be modified by the user, and then provided
(typically as "bench-params.json") to a benchmark orchestrator like
rickshaw-run.
