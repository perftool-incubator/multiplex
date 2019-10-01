# multiplex

## Introduction
When running a benchmark, it is often desirable to run it multiple ways, changing how the options are used, so you can get a full characterization of whatever you are testing.  For example, one might use several message sizes for a network test, or use different IO-engines for a storage test.  However, when executing a benchmark, most of them expect to have exactly one value for each option, like a message-size of just "16k" or an IO-engine of just "libaio".  Multiplex will translate your multi-value options into a list of multiple command-line statements that your benchmark understands.  Multiplex can also provide validation of the options and automatic conversion of the values if desired.

## Input and Output
Multiplex requires two types of input:

* A benchmark command with one or more values per option: --rw read,randread --ioengine libaio,sync
* A benchmark-specific config file which describes what options are valid and what values can be used for each option

With this, multiplex then provides a list of benchmark options.  For example:

<pre>#multiplex testing/test1/benchmark.json --this-string a,b --that-string c,d

--that-string c --this-string a --use-feature1 0
--that-string c --this-string b --use-feature1 0
--that-string d --this-string a --use-feature1 0
--that-string d --this-string b --use-feature1 0 </pre>

Note that the "--use-feature1" was added because benchmark.json has options in its "mandatory" section which are always included.

## Implementation Details and other Features

### Verification and Conversion
Multiplex provides a bit more than just generating all option permutations for your benchmark.  Since using many options with many values per option can generate potentially hundreds of individual tests, multiplex also provides option verification for your benchmark.  Verifying these options before submitting possibly hundreds of benchmark executions can save time if you happen to have an error in your test plan.

Within the benchmark-specific config file, options are categorized into groups, each group having a regular-expression that the option's *values* must adhere to.  For example, for the Fio benchmark [1], the options below all have their values verified with regex  "[0-9]+[kmgKMG]":

<pre>--bs
--filesize
--io_size
--mem</pre>

In this case, a value of "-102" or "abc" will not be valid, but a value of "1G" or "1024" is valid.

Multiplex also provides for an automatic conversion of values, and these conversions are specific to the groups the options are categorized into.  For example for the above options, all values use the regular-expression substitution [ "s/([0-9]+)[gG]/($1*1024).\"M\"/e","s/([0-9]+)[mM]/($1*1024).\"K\"/e" ].  In this case, all values in megabytes or gigabytes are converted to kilobytes.  This may be useful if you later search results, and you can then search on one type of unit (kilobytes) instead of having to parse multiple unit types.

### Benchmark Default Options
Within each of the benchmark's config file are sets of options called "default-sets".  There can be more than one default-set.  Each default-set is a collection of options which are used for specific use-cases.  They are provided as a convenience to the user, and as a "starter" set of options if the user is unfamimliar with the particular bechmark.  To see what default sets are available, just run multiplex this way:

<pre>multiplex testing/test1/benchmark.json --defaults list</pre>

This will generate a list of the default-sets for that benchmark, showing the name of each default-set and the options it uses: 
<pre># defaults available:
# full: --this-string a,b,c,d --this-size 1K,256M,1G --run-time 60s,1m,1h
# basic: --this-string a,b --this-size 256M --run-time 60s</pre>
 One can combine a default-set with their own options.  If a specific option is present in the default-set and also specified by the user, the last ocurrance of that option is what gets used.


### Grouping Options
Sometimes a user needs more control on how the permutations are generated.  For example, a user running Fio may want to test both sequential reads and sequential writes: "--rw read,write", but the user also needs to use different values for the "--ioengine" option and different values for the "--bs" option depending on what value is used for "--rw".  When "-rw" is testing for "read", the "--ioengine" values tested need to be "sync" and "libaio", and the values for "--bs" need to be "4k" and "16k".   However, when "write" is used for the "--rw" option, only "sync" is needed for "--ioengine" option and "256k" and "1024K" for the "--bs" option.  We need Multiplex to create option permutations on a subset of options, then again on another subset of options.  To restrict which options are used to generate the permutations, separate the options with "--", like the following:

<pre>multiplex /path/to/fio.json --rw write --ioengine libaio,sync --bs 4k,16k -- --rw read --ioengine sync --bs 256k,1024k</pre>

Multiplex will then generate permutations for just "-rw write --ioengine libaio,sync --bs 4k,16k", and then another permutation for just "--rw read --ioengine sync --bs 256k,1024k", yielding:

<pre>--rw write --ioengine libaio --bs 4k
--rw write --ioengine libaio --bs 16k
--rw write --ioengine sync --bs 4k
--rw write --ioengine libaio --bs 16k
--rw read --ioengine sync --bs 256k
--rw read --ioengine sync --bs 1024k</pre>

Occaisonally a user needs to iterate over multiple values, but each value needs to be used in lock-step for multiple options.  For example, someone may need both --iodepth and --iodepth_batch_complete_max to "4", then another test both options use "8", and a final test where both options use "16" for the Fio benchmark.  If the following were used, "--iodepth 4,8,16 --iodepth_batch_complete_max 4,8,16", there would be 9 tests, not 3.  To get just 3 tests, define a shared-value:

<pre>--[depth] 4,8,16 --iodepth [depth] --iodepth_batch_complete_max [depth]</pre>

This will result in the following permutations:

<pre>--iodepth 4  --iodepth_batch_complete_max 4
--iodepth 8  --iodepth_batch_complete_max 8
--iodepth 16  --iodepth_batch_complete_max 16</pre>

## Installation
### Dependencies
Multiplex is written in Perl and requires these modules:
<pre>Text::ParseWords
JSON::XS
Data::Dumper</pre>

If these modules are not installed in the default location, add the necessary library path to the existing PERL5_INC environment variable.

### Benchmarks
Mulitplex does not include benchmark config files, except config files of made-up benchmarks for unit-testing.  To use a real benchmark config file, see the following benchmark projects in the perftool-incubator organization:

[1] Fio

