# multiplex
Translates a JSON with multi-value parameters into a JSON with single-value parameters.

## Introduction
When running a benchmark, it is often desirable to run it multiple ways, changing how the options are used, so you can get a full characterization of whatever you are testing.  For example, one might use several message sizes for a network test, or use different IO-engines for a storage test.  However, when executing a benchmark, most of them expect to have exactly one value for each option, like a message-size of just "16k" or an IO-engine of just "libaio".  Multiplex will translate your multi-value options into a list of multiple command-line statements that your benchmark understands.

## Usage
```
./multiplex.py --input JSON/mv-params-input.json > /path/to/bench-params.json
```

## Input multi-value JSON
Multiplex requires a JSON file with the following format:
```
{
    "global-options":
    [
        {
            "name": "common-params",
            "params":
                [
                    {
                        "arg": "bs", "vals": [ "4k", "8k" ], "role": "client"
                    },
                    {
                        "arg": "rw", "vals": [ "read", "write" ]
                    }
                ]
        }
    ],
    "sets":
        [
            [
                {
                    "include": "common-params"
                },
                {
                    "arg": "ioengine", "vals": [ "sync" ]
                }
            ]
        ]
}
```

### global-options
The `global-options` section is required. It contains blocks of general configuration
data can be replicated and included in the `sets` section.
In this section, you may have an array of multi-value parameters that are common to
the test run as "common-params". Multi-value params are specified with the `args` and
`vals` keywords. The `role` key is optional and defaults to 'client' if omitted. Valid
roles are: "client", "server" and "all".

Also, you may have a block to define benchmark or tooling specific settings. Example:
"crucible-defaults".

These blocks must have "name" and "params" key values.

### sets
A data set of multi-value parameters is defined in each block inside the `sets` section.
The `sets` section is required and must have one or more set(s). Multi-value params are
specified with the `args` and `vals` keywords, identical to the "common-params" block
from the `global-options`. Likewise, the `role` key is optional and defaults to 'client'
if omitted. Valid roles are "client", "server" and "all".


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
