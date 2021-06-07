# multiplex
[![CI Actions Status](https://github.com/perftool-incubator/multiplex/workflows/unittest/badge.svg)](https://github.com/perftool-incubator/multiplex/actions)

Translates a JSON with multi-value parameters into a JSON with single-value parameters.

## Introduction
When running a benchmark, it is often desirable to run it multiple ways, changing how the options are used, so you can get a full characterization of whatever you are testing.  For example, one might use several message sizes for a network test, or use different IO-engines for a storage test.  However, when executing a benchmark, most of them expect to have exactly one value for each option, like a message-size of just "16k" or an IO-engine of just "libaio".  Multiplex will translate your multi-value options into a list of multiple command-line statements that your benchmark understands.

## Usage
```
./multiplex.py [--requirements JSON/requirements.json] --input JSON/mv-params-input.json > /path/to/bench-params.json
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
        [
            { "include": "common-params" },
            { "arg": "ioengine", "vals": [ "sync" ] }
        ]
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

## Requirements file
The requirements file defines all the validation and transformation parameters for a
specific benchmark. The file contains three main blocks: `default`, `mandatory` and
`validation`. The example below is a simplified version of fio benchmark requirements
file:
```
{
    "default": {
        "rw": ["read", "randread"],
        "bs": ["16k"]
    },
    "mandatory": {
        "write_hist_log": ["fio"],
        "log_hist_msec": ["10000"]
    },
    "validation": {
        "size_KMG" : {
            "description" : "bytes in k/K (1024), m/M (1024^2) or g/G (1024^3): 4k 16M 1g",
            "arguments" : [ "param1", "filesize", "io_size", "mem" ],
            "value" : "[0-9]+[kbmgKBMG]",
            "transform" : [ "s/([0-9]+)[gG]/($1*1024).\"M\"/e",
                            "s/([0-9]+)[mM]/($1*1024).\"K\"/e"
            ]
        }
    }
}
```

#### default
Defines all the default param values. Multiplex assumes these default params
if the param is not present in the mv-paramns.json input file.

#### mandatory
Defines all the mandatory params. Multiplex checks if all the mandatory params
are specified in the mv-params.json input file and it fails otherwise.

#### validation
Defines all the acceptable param values by validating the parameters with the
`value` regex. The values are transformed by applying the `transform` regex,
if present. The `transform` key is optional.


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
