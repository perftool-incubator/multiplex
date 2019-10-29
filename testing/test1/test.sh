#!/bin/bash

# Tests for:
# - Value with a comma, one with double-quotes escaped with '\',
#   another with single-quotes wrapping the value with double-quotes
# - Separate parameter-sets by using "--"
# - A mix of "--arg=val" and "--arg val" assignments
# - Specifying a default-set which exists (--defaults full), and using a param found in the default-set after (--this-string \"g,h\",i,j)
# - Attempt to override a mandatory default is not allowed (--use-feature 1)
# - Value transformations, M/G to K, false to 0

set -x

if [ -z "$MULTIPLEX_HOME" ]; then
    echo "Please set MULTIPLEX_HOME first"
    exit 2
fi

$MULTIPLEX_HOME/multiplex benchmark.json --that-string=\"b,c\",d,'"e,f"' --threads=5,6 --use-feature1=1 -- \
                                         --defaults full --this-string \"g,h\",i,j --use-feature2 true,false \
					 2>test-stderr.txt >test-stdout.txt
rc=$?
if [ $rc -gt 0 ]; then
    Mulitplex has non-zero exit code: $rc
    cat test-stderr.txt
    exit 3
fi
diff -Naurp test-ref-stderr.txt test-stderr.txt && /bin/rm test-stderr.txt || exit 1
diff -Naurp test-ref-stdout.txt test-stdout.txt && /bin/rm test-stdout.txt || exit 1
