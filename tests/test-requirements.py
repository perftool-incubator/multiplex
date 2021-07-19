#!/usr/bin/env python3

import pytest
import json
import multiplex
import re

class TestRequirements:

    requirements_json = "JSON/requirements-sample-fio.json"

    """Common function to load requirements"""
    @pytest.fixture(scope="function")
    def load_req(self, request):
        req_json = multiplex.load_requirements(request.param)
        return(req_json)

    """Test if requirements json file is successfully loaded"""
    @pytest.mark.parametrize("load_req", [ requirements_json ], indirect=True)
    def test_load_requirements(self, load_req):

        assert load_req is not None
        assert 'presets' in load_req

    """Test if validation dict is successfully created"""
    @pytest.mark.parametrize("load_req", [ requirements_json ], indirect=True)
    def test_create_validation_dict(self, load_req):
        val_dict = multiplex.create_validation_dict(load_req)

        assert val_dict is not None
        assert 'bs' in val_dict.keys()
