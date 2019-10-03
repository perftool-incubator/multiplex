#!/bin/bash

# Tests for:
# Uses options from test1, but benchmark.json file is missing
# Mulitplex should detect missing file and die

set -x

if [ -z "$MULTIPLEX_HOME" ]; then
    echo "Please set MULTIPLEX_HOME first"
    exit 2
fi

$MULTIPLEX_HOME/multiplex benchmark.json --that-string=\"b,c\",d,'"e,f"' --threads=5,6 --use-feature1=1 -- \
                                         --defaults full --this-string \"g,h\",i,j --use-feature2 true,false \
					 2>test-stderr.txt >test-stdout.txt
rc=$?
if [ $rc -eq 2 ]; then
    # exit code 2 is expected for this test
    diff -Naurp test-ref-stderr.txt test-stderr.txt && /bin/rm test-stderr.txt || exit 1
    diff -Naurp test-ref-stdout.txt test-stdout.txt && /bin/rm test-stdout.txt || exit 1
fi
