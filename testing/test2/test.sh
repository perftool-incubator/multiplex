#!/bin/bash

# Tests for:
# Defining a shared-value and using for mulitple options

set -x

if [ -z "$MULTIPLEX_HOME" ]; then
    echo "Please set MULTIPLEX_HOME first"
    exit 2
fi

$MULTIPLEX_HOME/multiplex benchmark.json --[my-numbers]=2,3,4,6,7,8 --that-string=[my-numbers] --threads=[my-numbers] \
                                         --other-string=hello \
					 2>test-stderr.txt >test-stdout.txt
rc=$?
if [ $rc -gt 0 ]; then
    Mulitplex has non-zero exit code: $rc
    cat test-stderr.txt
    exit 3
fi
diff -Naurp test-ref-stderr.txt test-stderr.txt && /bin/rm test-stderr.txt || exit 1
diff -Naurp test-ref-stdout.txt test-stdout.txt && /bin/rm test-stdout.txt || exit 1
