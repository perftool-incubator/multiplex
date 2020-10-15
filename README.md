# multiplex

## Introduction
When running a benchmark, it is often desirable to run it multiple ways, changing how the options are used, so you can get a full characterization of whatever you are testing.  For example, one might use several message sizes for a network test, or use different IO-engines for a storage test.  However, when executing a benchmark, most of them expect to have exactly one value for each option, like a message-size of just "16k" or an IO-engine of just "libaio".  Multiplex will translate your multi-value options into a list of multiple command-line statements that your benchmark understands.

## Input and Output
Multiplex requires a JSON from STDIN with the following format:
<pre>
{
    "common": [
        { "arg": "ioengine", "values": [ "sync", "aio" ] },
        { "arg": "runtime", "values": [ "60s", "120s" ] }
    ],
    "sets": [
        [
            { "arg": "bs", "values": [ "4k", "8k" ] },
            { "arg": "rw", "values": [ "read", "write" ] }
        ],
        [
            { "arg": "bs", "values": [ "16k", "32k" ] },
            { "arg": "rw", "values": [ "randread", "randwrite" ] },
            { "arg": "runtime", "values": [ "30s" ] }
        ]
    ]
}
</pre>

The common section is optonal, and the sets section is required.  At least one set is required.
A set of "multi-value parameters" are included in each set.  Each set, combined with the multi-value paramters in "common" (if it exists), will be used to expand to a new set of single-value parameters to STDOUT, like:

<pre>
[
    [ { "arg": "rw", "value": "read" }, { "arg": "bs", "value": "4k" }, { "arg": "runtime", "value": "60s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "write" }, { "arg": "bs", "value": "4k" }, { "arg": "runtime", "value": "60s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "read" }, { "arg": "bs", "value": "8k" }, { "arg": "runtime", "value": "60s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "write" }, { "arg": "bs", "value": "8k" }, { "arg": "runtime", "value": "60s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "read" }, { "arg": "bs", "value": "4k" }, { "arg": "runtime", "value": "120s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "write" }, { "arg": "bs", "value": "4k" }, { "arg": "runtime", "value": "120s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "read" }, { "arg": "bs", "value": "8k" }, { "arg": "runtime", "value": "120s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "write" }, { "arg": "bs", "value": "8k" }, { "arg": "runtime", "value": "120s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "read" }, { "arg": "bs", "value": "4k" }, { "arg": "runtime", "value": "60s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "write" }, { "arg": "bs", "value": "4k" }, { "arg": "runtime", "value": "60s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "read" }, { "arg": "bs", "value": "8k" }, { "arg": "runtime", "value": "60s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "write" }, { "arg": "bs", "value": "8k" }, { "arg": "runtime", "value": "60s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "read" }, { "arg": "bs", "value": "4k" }, { "arg": "runtime", "value": "120s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "write" }, { "arg": "bs", "value": "4k" }, { "arg": "runtime", "value": "120s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "read" }, { "arg": "bs", "value": "8k" }, { "arg": "runtime", "value": "120s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "write" }, { "arg": "bs", "value": "8k" }, { "arg": "runtime", "value": "120s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "randread" }, { "arg": "bs", "value": "16k" }, { "arg": "runtime", "value": "30s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "randread" }, { "arg": "bs", "value": "32k" }, { "arg": "runtime", "value": "30s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "randread" }, { "arg": "bs", "value": "16k" }, { "arg": "runtime", "value": "30s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "randread" }, { "arg": "bs", "value": "32k" }, { "arg": "runtime", "value": "30s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "randwrite" }, { "arg": "bs", "value": "16k" }, { "arg": "runtime", "value": "30s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "randwrite" }, { "arg": "bs", "value": "32k" }, { "arg": "runtime", "value": "30s" }, { "arg": "ioengine", "value": "sync" } ],
    [ { "arg": "rw", "value": "randwrite" }, { "arg": "bs", "value": "16k" }, { "arg": "runtime", "value": "30s" }, { "arg": "ioengine", "value": "aio" } ],
    [ { "arg": "rw", "value": "randwrite" }, { "arg": "bs", "value": "32k" }, { "arg": "runtime", "value": "30s" }, { "arg": "ioengine", "value": "aio" } ]
]
</pre>

This JSON can then optionally be modified by the user, and then provided (typically as "bench-params.json") to a benchmark orchestrator like rickshaw-run.

## Implementation Details

Multiplex is written in Go and requires the following packages:
* os
* fmt
* encoding/json
* io/ioutil
* github.com/xeipuuv/gojsonschema
