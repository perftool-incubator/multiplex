#!/usr/bin/env python3

import pytest
import json
import multiplex
import re

class TestRequirements:

    """Test if requirements json file is successfully loaded"""
    def test_load_requirements(self):
        requirements_json = "JSON/requirements-sample-fio.json"
        req_json = multiplex.load_requirements(requirements_json)

        assert req_json is not None
        assert 'presets' in req_json
