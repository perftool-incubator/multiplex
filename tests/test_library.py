import copy

import pytest

import multiplex


def _input_document():
    return {
        "sets": [
            {
                "params": [
                    {"arg": "size", "vals": ["1K", "2K"]},
                    {"arg": "mode", "vals": ["read", "write"]},
                ]
            }
        ]
    }


def test_expand_parameters_matches_the_existing_expansion_shape():
    document = _input_document()
    original = copy.deepcopy(document)

    result = multiplex.expand_parameters(document)

    assert result["count"] == 4
    assert result["truncated"] is False
    assert len(result["sets"]) == 4
    assert all(
        {param["arg"] for param in parameter_set} == {"size", "mode"}
        for parameter_set in result["sets"]
    )
    assert document == original


def test_expand_parameters_bounds_cartesian_products_before_materializing_them():
    result = multiplex.expand_parameters(_input_document(), max_results=2)

    assert result["count"] == 4
    assert result["returned"] == 2
    assert len(result["sets"]) == 2
    assert result["truncated"] is True


def test_expand_parameters_reports_invalid_input_structurally():
    with pytest.raises(multiplex.ExpansionError) as error:
        multiplex.expand_parameters({"sets": "not-an-array"})

    assert error.value.code == "invalid_input"


def test_expand_parameters_does_not_leak_requirements_between_calls():
    requirements = {
        "validations": {
            "mode-values": {
                "args": ["mode"],
                "vals": "^read$",
            }
        }
    }

    with pytest.raises(multiplex.ExpansionError):
        multiplex.expand_parameters(_input_document(), requirements_json=requirements)

    result = multiplex.expand_parameters(_input_document())
    assert result["count"] == 4
