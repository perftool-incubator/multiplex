package main

/*
Read some multi-value params in JSON like:
{
    "common": [
        { "arg": "runtime", "values": [ "60s" ] }
    ],
    "sets": [
        [
            { "arg": "bs", "values": [ "4k", "8k" ] },
            { "arg": "rw", "values": [ "read", "write" ] }
        ],
        [
            { "arg": "bs", "values": [ "16k", "32k" ] },
            { "arg": "rw", "values": [ "randread", "randwrite" ] }
        ]
    ]
}

And outupt mulitplexed, single-value params JSON like:
[
    [
        { "arg": "runtime", "value": "60s" },
        { 'arg': 'rw', 'value': 'read' },
        { 'arg': 'bs', 'value': '4k' }
    ],
    [
        { "arg": "runtime", "value": "60s" },
        { 'arg': 'rw', 'value': 'read' },
        { 'arg': 'bs', 'value': '8k' }
    ],
    [
        { "arg": "runtime", "value": "60s" },
        { 'arg': 'rw', 'value': 'randread' },
        { 'arg': 'bs', 'value': '4k' }
    ],
    [
        { "arg": "runtime", "value": "60s" },
        { 'arg': 'rw', 'value': 'randread' },
        { 'arg': 'bs', 'value': '8k' }
    ]
]
*/

import (
    "os"
    "fmt"
    "encoding/json"
    "io/ioutil"
    "github.com/xeipuuv/gojsonschema"
)
// sv = single-value
// mv = multi-value
type svParamType struct {
    Arg string `json:"arg"`
    Value string `json:"value"`
}
type svParamSetType []svParamType
type svParamSetsType []svParamSetType
type valuesType []string
type mvParamType struct {
    Arg string `json:"arg"`
    Values valuesType `json:"values"`
}
type mvParamSetType []mvParamType
type mvParamSetsType []mvParamSetType
type inputParamType struct {
    Common mvParamSetType `json:"common"`
    Sets mvParamSetsType `json:"sets"`
}

func buildSingleValParamSets(multiValParams mvParamSetType) svParamSetsType {
    var singleValParamSets svParamSetsType
    if len(multiValParams) > 1 {
        multiValParam, multiValParams := multiValParams[0], multiValParams[1:]
	    for _, val := range multiValParam.Values {
            thisSingleValParamSets := buildSingleValParamSets(multiValParams)
            for _, thisSingleValParamSet := range thisSingleValParamSets {
                thisSingleValParamSet = append(thisSingleValParamSet, svParamType{Arg: multiValParam.Arg, Value: val,})
                singleValParamSets = append(singleValParamSets, thisSingleValParamSet)
            }
	    }
    } else {
	    for _, val := range multiValParams[0].Values {
            singleValParamSet := svParamSetType{svParamType{Arg: multiValParams[0].Arg, Value: val,}}
            singleValParamSets = append(singleValParamSets, singleValParamSet)
        }
    }
    return singleValParamSets
}

func main() {
    validate := false
    data, _ := ioutil.ReadAll(os.Stdin)
    inputParams := inputParamType{}
    merr := json.Unmarshal([]byte(data),&inputParams)
    if merr != nil {
        fmt.Printf("Error reading input:\n")
        fmt.Println(merr)
        return
    }

    if validate {
        documentLoader := gojsonschema.NewGoLoader(inputParams)
        schemaLoader := gojsonschema.NewReferenceLoader("file://schema/multi-val-params.json")
        result, err := gojsonschema.Validate(schemaLoader, documentLoader)
        if err != nil {
            panic(err.Error())
        }
        if ! result.Valid() {
            fmt.Printf("The document is not valid. see errors :\n")
            for _, desc := range result.Errors() {
                fmt.Printf("- %s\n", desc)
            }
            return
        }
    }

    var svps svParamSetsType
    for _, multiValParamSet := range inputParams.Sets {
        // Aggregate the "combined" multi-val params with one of the "Sets"
        // into a map in order to avoid duplicates.
        m := make(map[string]valuesType)
        for _, thisMvParam := range inputParams.Common {
            m[thisMvParam.Arg] = thisMvParam.Values
        }
        for _, thisMvParam := range multiValParamSet {
            m[thisMvParam.Arg] = thisMvParam.Values
        }
        // Now put back in a multi-val param-set to expand
        var mvParamSet mvParamSetType
        for thisArg, _ := range m {
            var mvParam mvParamType
            mvParam.Arg = thisArg
            mvParam.Values = m[thisArg]
            mvParamSet  = append(mvParamSet, mvParam)
        }
        svps = append(svps,buildSingleValParamSets(mvParamSet)...)
    }
    b, err := json.MarshalIndent(svps, "", "    ")
    if err == nil {
        fmt.Println(string(b))
    } else {
        fmt.Printf("json error:%v%v\n", err)
    }
}
