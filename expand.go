package main

/*
Read some multi-value params in JSON like:
[
    { 'arg': 'rw', 'values': [ 'read', 'randread' ] },
    { 'arg': 'bs', 'values': [ '4k', '8k' ] }
]

And outupt mulitplexed, single-value params JSON like:
[
    [
        { 'arg': 'rw', 'value': 'read' },
        { 'arg': 'bs', 'value': '4k' }
    ],
    [
        { 'arg': 'rw', 'value': 'read' },
        { 'arg': 'bs', 'value': '8k' }
    ],
    [
        { 'arg': 'rw', 'value': 'randread' },
        { 'arg': 'bs', 'value': '4k' }
    ],
    [
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
type mvParamType struct {
    Arg string `json:"arg"`
    Values []string `json:"values"`
}
type mvParamSetType []mvParamType
type svParamType struct {
    Arg string `json:"arg"`
    Value string `json:"value"`
}
type svParamSetType []svParamType
type svParamSetsType []svParamSetType

type Employee struct {
    id   int
    name string
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
    inputParams := mvParamSetType{}
    merr := json.Unmarshal([]byte(data),&inputParams)
    if merr != nil {
        //fmt.Println(merr)
    //} else {
        fmt.Printf("json conversion error:%v\n", merr)
    }
    //fmt.Printf("%v\n", inputParams)

    if validate {
        documentLoader := gojsonschema.NewGoLoader(inputParams)
        schemaLoader := gojsonschema.NewReferenceLoader("file://schema/multi-val-params.json")
        result, err := gojsonschema.Validate(schemaLoader, documentLoader)
        if err != nil {
            panic(err.Error())
        }
        if ! result.Valid() {
            //fmt.Printf("The document is valid\n")
        //} else {
            fmt.Printf("The document is not valid. see errors :\n")
            for _, desc := range result.Errors() {
                fmt.Printf("- %s\n", desc)
            }
            return
        }
    }

    var svps svParamSetsType
    svps = buildSingleValParamSets(inputParams)
    b, err := json.MarshalIndent(svps, "", "    ")
    if err == nil {
        fmt.Println(string(b))
    } else {
        fmt.Printf("json error:%v%v\n", err)
    }
}
