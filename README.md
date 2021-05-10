# multiplex
Translates a JSON with multi-value parameters into a JSON with single-value parameters.

## Introduction
When running a benchmark, it is often desirable to run it multiple ways, changing how the options are used, so you can get a full characterization of whatever you are testing.  For example, one might use several message sizes for a network test, or use different IO-engines for a storage test.  However, when executing a benchmark, most of them expect to have exactly one value for each option, like a message-size of just "16k" or an IO-engine of just "libaio".  Multiplex will translate your multi-value options into a list of multiple command-line statements that your benchmark understands.

## Usage
```
./multiplex.py --input JSON/mv-params-input.json > /path/to/bench-params.json
```

## Input and Output
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
                    "arg": "bs", "vals": [ "4k", "8k" ]
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

The `global-options` and the `sets` sections are both required.
A set of "multi-value parameters" is included in each set.  Each set, combined
with the multi-value paramters in "global-options", will be used to expand to a new set
of single-value parameters to STDOUT, like the sample generated in
`JSON/bench-params-output.json`:
```
[
    [
        {
            "arg": "bs",
            "val": "4k"
        },
        {
            "arg": "rw",
            "val": "read"
        },
        {
            "arg": "ioengine",
            "val": "sync"
        }
    ],
    [
        {
            "arg": "bs",
            "val": "4k"
        },
        {
            "arg": "rw",
            "val": "write"
        },
        {
            "arg": "ioengine",
            "val": "sync"
        }
    ],
    [
        {
            "arg": "bs",
            "val": "8k"
        },
        {
            "arg": "rw",
            "val": "read"
        },
        {
            "arg": "ioengine",
            "val": "sync"
        }
    ],
    [
        {
            "arg": "bs",
            "val": "8k"
        },
        {
            "arg": "rw",
            "val": "write"
        },
        {
            "arg": "ioengine",
            "val": "sync"
        }
    ]
]
```

This JSON can then optionally be modified by the user, and then provided
(typically as "bench-params.json") to a benchmark orchestrator like
rickshaw-run.
